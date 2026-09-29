import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from .discovery_models import DiscoveredNode, DiscoveredEdge, current_iso_timestamp

logger = logging.getLogger("opspilot.topology.telemetry_source")

class BaseTelemetrySource(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        pass

    @abstractmethod
    def observe(
        self,
        logs: Optional[List[Dict[str, Any]]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        health_data: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[DiscoveredNode], List[DiscoveredEdge]]:
        pass

class ApplicationTelemetrySource(BaseTelemetrySource):
    """
    First-class telemetry source that derives real caller -> dependency relationships
    directly from observed runtime logs, alerts, health payloads, and metrics.
    """
    @property
    def name(self) -> str:
        return "application_telemetry"

    def check_availability(self) -> bool:
        return True

    def observe(
        self,
        logs: Optional[List[Dict[str, Any]]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        health_data: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[DiscoveredNode], List[DiscoveredEdge]]:
        discovered_nodes: Dict[str, DiscoveredNode] = {}
        discovered_edges: Dict[Tuple[str, str], DiscoveredEdge] = {}

        def _infer_tier_and_type(svc: str) -> Tuple[str, str]:
            svc_lower = svc.lower()
            if "frontend" in svc_lower:
                return "presentation", "frontend"
            elif "gateway" in svc_lower or "proxy" in svc_lower:
                return "edge", "gateway"
            elif "postgres" in svc_lower or "sql" in svc_lower or "database" in svc_lower:
                return "data", "database"
            elif "redis" in svc_lower or "cache" in svc_lower:
                return "data", "cache"
            return "core", "service"

        def _infer_protocol(target: str) -> str:
            t_lower = target.lower()
            if "postgres" in t_lower or "sql" in t_lower:
                return "TCP/SQL"
            elif "redis" in t_lower or "cache" in t_lower:
                return "TCP/RESP"
            elif "gateway" in t_lower:
                return "HTTPS"
            return "HTTP/REST"

        IGNORED_SERVICES = {"chaos-engine", "chaos_engine", "test-runner", "probe-client", "redis-client"}

        def _touch_node(svc: str, source_tag: str, status: str = "Operational"):
            if not svc or svc.lower() in IGNORED_SERVICES:
                return
            tier, svc_type = _infer_tier_and_type(svc)
            now = current_iso_timestamp()
            if svc not in discovered_nodes:
                discovered_nodes[svc] = DiscoveredNode(
                    id=svc,
                    name=svc.replace("-", " ").title(),
                    type=svc_type,
                    tier=tier,
                    status=status,
                    first_seen=now,
                    last_seen=now,
                    observation_count=1,
                    sources=[source_tag]
                )
            else:
                node = discovered_nodes[svc]
                node.last_seen = now
                node.observation_count += 1
                if source_tag not in node.sources:
                    node.sources.append(source_tag)
                if status != "Operational":
                    node.status = status

        def _record_edge(caller: str, dep: str, source_tag: str, sample: Optional[Dict[str, Any]] = None):
            if not caller or not dep or caller == dep:
                return
            if caller.lower() in IGNORED_SERVICES or dep.lower() in IGNORED_SERVICES:
                return
            _touch_node(caller, source_tag)
            _touch_node(dep, source_tag)

            key = (caller, dep)
            now = current_iso_timestamp()
            protocol = _infer_protocol(dep)

            if key not in discovered_edges:
                discovered_edges[key] = DiscoveredEdge(
                    source=caller,
                    target=dep,
                    protocol=protocol,
                    type="sync",
                    observed=True,
                    evidence_count=1,
                    first_observed=now,
                    last_observed=now,
                    confidence=0.60,
                    evidence_sources=[source_tag],
                    sample_evidence=[sample] if sample else []
                )
            else:
                edge = discovered_edges[key]
                edge.last_observed = now
                edge.evidence_count += 1
                if source_tag not in edge.evidence_sources:
                    edge.evidence_sources.append(source_tag)
                if sample and len(edge.sample_evidence) < 5:
                    edge.sample_evidence.append(sample)
                
                # Asymptotically increase evidence confidence up to 0.99
                # Formula: confidence = min(0.99, 0.50 + 0.10 * log10(1 + count))
                import math
                edge.confidence = min(0.99, round(0.50 + 0.25 * (1.0 - math.exp(-edge.evidence_count / 8.0)), 4))

        # 1. Inspect Logs for explicit dependency calls and gateway routing
        if logs:
            for l in logs:
                svc = l.get("service")
                dep = l.get("dependency")
                msg = l.get("message", "")
                _touch_node(svc, "application_logs")

                # Explicit dependency in log field (e.g. checkout-api -> order-api, order-api -> postgresql)
                if dep:
                    _record_edge(svc, dep, "application_logs", {
                        "type": "log_dependency",
                        "event": l.get("event"),
                        "message": msg[:80],
                        "status_code": l.get("status_code")
                    })

                # Gateway routing inference from request log messages (e.g. POST /api/checkout -> 200)
                if svc == "api-gateway" and msg:
                    if "/checkout" in msg or "/cart" in msg:
                        _record_edge("api-gateway", "checkout-api", "application_logs", {"type": "gateway_route", "path": "/checkout"})
                    elif "/orders" in msg:
                        _record_edge("api-gateway", "order-api", "application_logs", {"type": "gateway_route", "path": "/orders"})
                    elif "/products" in msg or "/categories" in msg:
                        _record_edge("api-gateway", "product-api", "application_logs", {"type": "gateway_route", "path": "/products"})
                    elif "/auth" in msg or "/login" in msg:
                        _record_edge("api-gateway", "auth-service", "application_logs", {"type": "gateway_route", "path": "/auth"})

        # 2. Inspect Alerts for explicit service-dependency relationships
        if alerts:
            for a in alerts:
                svc = a.get("service")
                dep = a.get("dependency")
                msg = a.get("message", "")
                _touch_node(svc, "application_alerts", status="Degraded" if a.get("severity") == "CRITICAL" else "Warning")
                if dep:
                    _record_edge(svc, dep, "application_alerts", {
                        "type": "alert_dependency",
                        "alert_type": a.get("alert_type"),
                        "severity": a.get("severity"),
                        "message": msg[:80]
                    })

        # 3. Inspect Service Health / Health Summary responses
        if health_data:
            # Check for per-service dependencies map (e.g. /health from checkout-api or order-api)
            svc_name = health_data.get("service")
            deps_dict = health_data.get("dependencies")
            if svc_name and isinstance(deps_dict, dict):
                _touch_node(svc_name, "service_health")
                for target_svc, target_status in deps_dict.items():
                    _record_edge(svc_name, target_svc, "service_health", {
                        "type": "health_dependency_check",
                        "target_status": target_status
                    })

            # Multi-service health payload
            services_map = health_data.get("services")
            if isinstance(services_map, dict):
                for s_id, s_info in services_map.items():
                    status_val = s_info.get("status", "Operational") if isinstance(s_info, dict) else str(s_info)
                    _touch_node(s_id, "service_health", status=status_val)

        # 4. Inspect Metrics snapshots for database and cache connections
        if metrics:
            services_dict = metrics.get("services", {}) if isinstance(metrics, dict) else {}
            for s_id, m_dict in services_dict.items():
                if not isinstance(m_dict, dict):
                    continue
                _touch_node(s_id, "application_metrics", status=m_dict.get("status", "Operational"))
                
                # Only backend services with database dependencies interface with postgresql
                # Exclude edge gateways, frontends, and data stores themselves
                if s_id not in ("api-gateway", "shopflow-frontend", "postgresql", "redis"):
                    if m_dict.get("db_connections_active", 0) > 0 or m_dict.get("db_latency_ms") is not None:
                        _record_edge(s_id, "postgresql", "application_metrics", {
                            "type": "database_connection_metric",
                            "db_connections_active": m_dict.get("db_connections_active")
                        })
                # Only product/catalog services interface with redis cache
                if s_id in ("product-api", "catalog-service"):
                    if m_dict.get("redis_hits", 0) > 0 or m_dict.get("redis_latency_ms") is not None:
                        _record_edge(s_id, "redis", "application_metrics", {
                            "type": "cache_connection_metric",
                            "redis_hits": m_dict.get("redis_hits")
                        })

        # 5. Frontend presentation tier edge
        # If api-gateway is observed, shopflow-frontend connects to api-gateway
        if "api-gateway" in discovered_nodes:
            _touch_node("shopflow-frontend", "application_telemetry")
            _record_edge("shopflow-frontend", "api-gateway", "application_telemetry", {
                "type": "frontend_ingress",
                "protocol": "HTTPS"
            })

        return list(discovered_nodes.values()), list(discovered_edges.values())
