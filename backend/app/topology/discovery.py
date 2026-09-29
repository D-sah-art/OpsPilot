import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from .discovery_models import DiscoveredNode, DiscoveredEdge, DiscoveredTopologyResult, current_iso_timestamp
from .telemetry_source import BaseTelemetrySource, ApplicationTelemetrySource
from .grafana_source import GrafanaTelemetrySource, grafana_telemetry_source
from .graph import dependency_graph

logger = logging.getLogger("opspilot.topology.discovery")

class TopologyDiscoveryEngine:
    """
    Autonomous, Read-Only Topology Discovery Engine.
    Observes real runtime telemetry from applications and optional Grafana instance,
    accumulates dependency evidence, tracks confidence, and produces the normalized
    DependencyGraph for OpsPilot 8-D correlation and RCA.
    
    If dynamic observations are cold or unavailable, gracefully falls back to the
    configured topology specification.
    """
    def __init__(
        self,
        sources: Optional[List[BaseTelemetrySource]] = None,
        grafana_source: Optional[GrafanaTelemetrySource] = None
    ):
        self.app_source = ApplicationTelemetrySource()
        self.grafana_source = grafana_source or grafana_telemetry_source
        self.sources: List[BaseTelemetrySource] = sources or [self.app_source, self.grafana_source]
        
        self._lock = threading.Lock()
        self.discovered_nodes: Dict[str, DiscoveredNode] = {}
        self.discovered_edges: Dict[Tuple[str, str], DiscoveredEdge] = {}
        
        # Fallback topology storage
        self.fallback_nodes: List[Dict[str, Any]] = []
        self.fallback_edges: List[Dict[str, Any]] = []
        
        self.last_discovery_time: Optional[str] = None
        self.last_discovery_source: str = "Configured Fallback"
        self.is_active_discovery: bool = False

    def register_fallback_topology(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        with self._lock:
            self.fallback_nodes = nodes
            self.fallback_edges = edges
            
            # Seed baseline nodes if not present
            for n_dict in nodes:
                nid = n_dict.get("id")
                if nid and nid not in self.discovered_nodes:
                    self.discovered_nodes[nid] = DiscoveredNode(
                        id=nid,
                        name=n_dict.get("name", nid),
                        type=n_dict.get("type", "service"),
                        tier=n_dict.get("tier", "core"),
                        port=n_dict.get("port"),
                        criticality=n_dict.get("criticality", "medium"),
                        status=n_dict.get("status", "Operational"),
                        sources=["configuration"],
                        first_seen=current_iso_timestamp(),
                        last_seen=current_iso_timestamp(),
                        observation_count=0
                    )
            
            # Seed baseline edges if not present (unobserved until validated by telemetry)
            for e_dict in edges:
                src = e_dict.get("source")
                tgt = e_dict.get("target")
                if src and tgt and (src, tgt) not in self.discovered_edges:
                    self.discovered_edges[(src, tgt)] = DiscoveredEdge(
                        source=src,
                        target=tgt,
                        protocol=e_dict.get("protocol", "HTTP/REST"),
                        type=e_dict.get("type", "sync"),
                        criticality=e_dict.get("criticality", "medium"),
                        observed=False,
                        evidence_count=0,
                        first_observed=current_iso_timestamp(),
                        last_observed=current_iso_timestamp(),
                        confidence=0.50,
                        evidence_sources=["configuration"]
                    )
            
            if not any(e.observed for e in self.discovered_edges.values()):
                dependency_graph.load_from_topology(nodes, edges)
                self.last_discovery_source = "Configured Fallback"

    def discover_from_sync(
        self,
        fallback_topology: Optional[Dict[str, Any]] = None,
        logs: Optional[List[Dict[str, Any]]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        health_data: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> DiscoveredTopologyResult:
        """
        Processes a live synchronization batch.
        Extracts observations from application telemetry and Grafana,
        accumulates evidence, updates the global DependencyGraph, and returns the result.
        """
        if fallback_topology:
            self.register_fallback_topology(
                fallback_topology.get("nodes", []),
                fallback_topology.get("edges", [])
            )

        with self._lock:
            # 1. Run Application Telemetry Source
            app_nodes, app_edges = self.app_source.observe(
                logs=logs,
                alerts=alerts,
                metrics=metrics,
                health_data=health_data,
                events=events
            )
            self._merge_observations(app_nodes, app_edges)

            # 2. Run Grafana Source (Optional, Read-Only)
            grafana_nodes, grafana_edges = self.grafana_source.observe(
                logs=logs,
                alerts=alerts,
                metrics=metrics,
                health_data=health_data,
                events=events
            )
            self._merge_observations(grafana_nodes, grafana_edges)

            now = current_iso_timestamp()
            self.last_discovery_time = now

            # Determine whether dynamic observations have been recorded
            has_dynamic_observations = (
                any(e.observed for e in self.discovered_edges.values()) or
                any(n.observation_count > 0 for n in self.discovered_nodes.values())
            )
            
            if has_dynamic_observations:
                self.is_active_discovery = True
                source_str = "Observed Runtime Telemetry & Grafana" if self.grafana_source.is_connected else "Observed Runtime Telemetry"
                self.last_discovery_source = source_str
                
                final_nodes = [n.to_dict() for n in self.discovered_nodes.values()]
                final_edges = [e.to_dict() for e in self.discovered_edges.values()]
                
                # Load discovered topology into the active NetworkX DependencyGraph
                dependency_graph.load_from_topology(final_nodes, final_edges)
                
                logger.info(
                    f"Dynamic Topology Discovery: Active with {len(final_nodes)} services, "
                    f"{len(final_edges)} dependencies. Source: {source_str}"
                )
                
                return DiscoveredTopologyResult(
                    source="discovered",
                    discovered_at=now,
                    discovery_source=source_str,
                    grafana_connected=self.grafana_source.is_connected,
                    grafana_status=self.grafana_source.last_check_status,
                    total_nodes=len(final_nodes),
                    total_edges=len(final_edges),
                    nodes=final_nodes,
                    edges=final_edges,
                    evidence_summary=self._build_evidence_summary()
                )
            else:
                # Graceful fallback to configured topology
                self.is_active_discovery = False
                self.last_discovery_source = "Configured Fallback"
                
                nodes_to_load = self.fallback_nodes if self.fallback_nodes else [n.to_dict() for n in self.discovered_nodes.values()]
                edges_to_load = self.fallback_edges if self.fallback_edges else [e.to_dict() for e in self.discovered_edges.values()]
                
                if nodes_to_load or edges_to_load:
                    dependency_graph.load_from_topology(nodes_to_load, edges_to_load)
                
                return DiscoveredTopologyResult(
                    source="fallback",
                    discovered_at=now,
                    discovery_source="Configured Fallback (Telemetry Cold)",
                    grafana_connected=self.grafana_source.is_connected,
                    grafana_status=self.grafana_source.last_check_status,
                    total_nodes=len(nodes_to_load),
                    total_edges=len(edges_to_load),
                    nodes=nodes_to_load,
                    edges=edges_to_load,
                    evidence_summary={"status": "fallback_active", "reason": "No runtime observations recorded yet"}
                )

    def _merge_observations(self, nodes: List[DiscoveredNode], edges: List[DiscoveredEdge]):
        IGNORED = {"chaos-engine", "chaos_engine", "test-runner", "probe-client", "redis-client"}
        for n in nodes:
            if n.id.lower() in IGNORED:
                continue
            if n.id not in self.discovered_nodes:
                self.discovered_nodes[n.id] = n
            else:
                existing = self.discovered_nodes[n.id]
                existing.last_seen = n.last_seen
                existing.observation_count += n.observation_count
                for s in n.sources:
                    if s not in existing.sources:
                        existing.sources.append(s)
                if n.status != "Operational":
                    existing.status = n.status

        for e in edges:
            if e.source.lower() in IGNORED or e.target.lower() in IGNORED:
                continue
            key = (e.source, e.target)
            if key not in self.discovered_edges:
                self.discovered_edges[key] = e
            else:
                existing = self.discovered_edges[key]
                existing.observed = True
                existing.last_observed = e.last_observed
                existing.evidence_count += e.evidence_count
                for s in e.evidence_sources:
                    if s not in existing.evidence_sources:
                        existing.evidence_sources.append(s)
                for s_ev in e.sample_evidence:
                    if len(existing.sample_evidence) < 5:
                        existing.sample_evidence.append(s_ev)
                import math
                existing.confidence = min(0.99, round(0.50 + 0.25 * (1.0 - math.exp(-existing.evidence_count / 8.0)), 4))

    def _build_evidence_summary(self) -> Dict[str, Any]:
        return {
            "total_observations": sum(e.evidence_count for e in self.discovered_edges.values()),
            "sources": list(set(s for e in self.discovered_edges.values() for s in e.evidence_sources)),
            "average_edge_confidence": round(
                sum(e.confidence for e in self.discovered_edges.values()) / max(1, len(self.discovered_edges)), 3
            ) if self.discovered_edges else 0.0,
            "edges_evidence": {
                f"{e.source}->{e.target}": {
                    "count": e.evidence_count,
                    "confidence": e.confidence,
                    "sources": e.evidence_sources,
                    "last_observed": e.last_observed
                }
                for e in self.discovered_edges.values()
            }
        }

    def get_current_topology_dict(self) -> Dict[str, Any]:
        """
        Returns backward-compatible dictionary for GET /api/topology
        augmented with discovery metadata.
        """
        with self._lock:
            now = self.last_discovery_time or current_iso_timestamp()
            IGNORED = {"chaos-engine", "chaos_engine", "test-runner", "probe-client", "redis-client"}
            if self.is_active_discovery and self.discovered_nodes:
                nodes = [n.to_dict() for n in self.discovered_nodes.values() if n.id.lower() not in IGNORED]
                edges = [e.to_dict() for e in self.discovered_edges.values() if e.source.lower() not in IGNORED and e.target.lower() not in IGNORED]
                source_mode = "discovered"
            else:
                nodes = [n for n in (self.fallback_nodes if self.fallback_nodes else dependency_graph.get_nodes()) if (n.get("id") or "").lower() not in IGNORED]
                edges = [e for e in (self.fallback_edges if self.fallback_edges else dependency_graph.get_edges()) if (e.get("source") or "").lower() not in IGNORED and (e.get("target") or "").lower() not in IGNORED]
                source_mode = "fallback"

            evidence_data = self._build_evidence_summary() if source_mode == "discovered" else {"status": "fallback_active", "reason": "No dynamic observations recorded yet"}

            return {
                "source": source_mode,
                "discovered_at": now,
                "discovery_source": self.last_discovery_source,
                "grafana_connected": self.grafana_source.is_connected,
                "grafana_status": self.grafana_source.last_check_status,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "nodes": nodes,
                "edges": edges,
                "evidence": evidence_data,
                "evidence_summary": evidence_data
            }

    def reset(self):
        with self._lock:
            self.discovered_nodes.clear()
            self.discovered_edges.clear()
            self.is_active_discovery = False
            self.last_discovery_source = "Configured Fallback"

topology_discovery_engine = TopologyDiscoveryEngine()
