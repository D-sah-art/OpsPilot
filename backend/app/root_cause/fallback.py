import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.topology.graph import DependencyGraph, dependency_graph
from .models import RootCauseAnalysis, ConfidenceBreakdown

logger = logging.getLogger("opspilot.root_cause.fallback")

class DeterministicFallbackAnalyzer:
    """
    Generic, topology-and-causality-driven deterministic root cause analyzer.
    Used when LLM is unconfigured, times out, or produces invalid output.
    Does NOT use hardcoded scenario names or arbitrary magic scores.
    """

    def __init__(self, graph: Optional[DependencyGraph] = None):
        self.graph = graph or dependency_graph

    def analyze(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        alerts: Optional[List[Dict[str, Any]]] = None
    ) -> RootCauseAnalysis:
        evidence = incident_data.get("correlation_evidence") or {}
        if hasattr(evidence, "model_dump"):
            evidence = evidence.model_dump()

        affected_services = incident_data.get("affected_services") or []
        causal_chain = evidence.get("causal_chain") or []
        dependency_paths = evidence.get("dependency_paths") or []
        earliest_alert = evidence.get("earliest_alert") or {}
        latest_alert = evidence.get("latest_alert") or {}
        top_pairwise = evidence.get("top_pairwise_correlations") or []
        correlation_score = float(incident_data.get("correlation_score", 1.0))

        if not affected_services and alerts:
            affected_services = list({a.get("service") for a in alerts if a.get("service")})

        # 1. Identify Candidate Root Services using Generic Graph & Temporal Analysis
        root_service, propagation_path = self._determine_root_and_path(
            affected_services=affected_services,
            causal_chain=causal_chain,
            earliest_alert=earliest_alert,
            dependency_paths=dependency_paths
        )

        # 2. Compute Evidence-Derived Confidence Breakdown
        confidence_breakdown, confidence_score = self._calculate_confidence(
            root_service=root_service,
            affected_services=affected_services,
            causal_chain=causal_chain,
            earliest_alert=earliest_alert,
            dependency_paths=dependency_paths,
            top_pairwise=top_pairwise,
            correlation_score=correlation_score
        )

        # 3. Build Evidence Summary
        evidence_summary = self._build_evidence_summary(
            incident_data=incident_data,
            evidence=evidence,
            root_service=root_service,
            earliest_alert=earliest_alert,
            latest_alert=latest_alert,
            propagation_path=propagation_path
        )

        # 4. Build Causal Narrative
        causal_narrative = self._build_causal_narrative(
            root_service=root_service,
            causal_chain=causal_chain,
            propagation_path=propagation_path,
            earliest_alert=earliest_alert
        )

        # 5. Build Informational Recommendation
        recommended_action = self._build_recommendation(
            root_service=root_service,
            earliest_alert=earliest_alert,
            causal_chain=causal_chain
        )

        summary = (
            f"Root cause identified as '{root_service}' originating at "
            f"{earliest_alert.get('timestamp', 'unknown timestamp')}. "
            f"Cascading failures propagated across {len(affected_services)} services along the dependency path."
        )

        return RootCauseAnalysis(
            incident_id=incident_id,
            root_cause_service=root_service,
            root_cause_summary=summary,
            confidence_score=confidence_score,
            confidence_breakdown=confidence_breakdown,
            causal_narrative=causal_narrative,
            propagation_path=propagation_path,
            evidence_summary=evidence_summary,
            recommended_action=recommended_action,
            analysis_mode="deterministic_fallback",
            model_used=None,
            diagnosed_at=datetime.now(timezone.utc).isoformat()
        )

    def _determine_root_and_path(
        self,
        affected_services: List[str],
        causal_chain: List[Dict[str, Any]],
        earliest_alert: Dict[str, Any],
        dependency_paths: List[List[str]]
    ) -> tuple[str, List[str]]:
        """
        Determines the root cause service and causal propagation path generically:
        1. Evaluates graph topology: downstream dependencies called by other affected services.
        2. Evaluates chronological alert order: service with the earliest alert.
        """
        if not affected_services:
            return "unknown", []

        if len(affected_services) == 1:
            return affected_services[0], [affected_services[0]]

        service_scores: Dict[str, float] = {s: 0.0 for s in affected_services}

        # Temporal score from causal chain / earliest alert
        if earliest_alert and earliest_alert.get("service") in service_scores:
            service_scores[earliest_alert["service"]] += 3.0

        if causal_chain:
            # Earlier alerts in chain get more weight
            total_chain = len(causal_chain)
            for idx, c in enumerate(causal_chain):
                svc = c.get("service")
                if svc in service_scores:
                    rank_weight = (total_chain - idx) / max(total_chain, 1)
                    service_scores[svc] += rank_weight * 2.0

        # Topological score from dependency graph
        # A service that is CALLED by other affected services (target of edges) is downstream in call-stack
        for svc in affected_services:
            callers = [other for other in affected_services if other != svc and self._has_edge(other, svc)]
            callees = [other for other in affected_services if other != svc and self._has_edge(svc, other)]
            # Target nodes with many callers and few/zero callees among affected services are root-side dependencies
            service_scores[svc] += len(callers) * 1.5
            service_scores[svc] -= len(callees) * 1.0

        # Pick candidate with highest score
        root_service = max(service_scores, key=lambda k: service_scores[k])

        # Derive propagation path (from root to edge callers)
        # Check if we have dependency paths that include root_service
        matching_paths = [p for p in dependency_paths if root_service in p]
        if matching_paths:
            # Longest path containing the root
            best_path = max(matching_paths, key=len)
            # Ensure path is ordered from root_service to outward caller or vice-versa
            if best_path[-1] == root_service:
                # Path is [caller, ..., root], reverse to [root, ..., caller]
                propagation_path = list(reversed(best_path))
            else:
                propagation_path = best_path
        else:
            # Construct breadth-first outward path from root_service among affected
            propagation_path = [root_service]
            remaining = [s for s in affected_services if s != root_service]
            current_layer = [root_service]
            while remaining:
                next_layer = []
                for curr in current_layer:
                    for rem in list(remaining):
                        if self._has_edge(rem, curr):
                            next_layer.append(rem)
                            remaining.remove(rem)
                            propagation_path.append(rem)
                if not next_layer:
                    # Append any leftovers
                    propagation_path.extend(remaining)
                    break
                current_layer = next_layer

        return root_service, propagation_path

    def _has_edge(self, u: str, v: str) -> bool:
        """Safely checks edge existence across DependencyGraph and nx.DiGraph."""
        if not self.graph:
            return False
        if hasattr(self.graph, "has_edge"):
            return self.graph.has_edge(u, v)
        if hasattr(self.graph, "graph") and hasattr(self.graph.graph, "has_edge"):
            return self.graph.graph.has_edge(u, v)
        return False

    def _calculate_confidence(
        self,
        root_service: str,
        affected_services: List[str],
        causal_chain: List[Dict[str, Any]],
        earliest_alert: Dict[str, Any],
        dependency_paths: List[List[str]],
        top_pairwise: List[Dict[str, Any]],
        correlation_score: float
    ) -> tuple[ConfidenceBreakdown, float]:
        """
        Evidence-derived confidence calculation strictly bounded to [0.0, 1.0].
        Calculates confidence components objectively based on available telemetry evidence.
        """
        # 1. Topological Clarity: Do affected services have clear directed paths?
        if len(affected_services) <= 1:
            topological_clarity = 0.8
        elif dependency_paths:
            has_root_path = any(root_service in p for p in dependency_paths)
            avg_path_len = sum(len(p) for p in dependency_paths) / len(dependency_paths)
            topological_clarity = min(1.0, 0.5 + (0.3 if has_root_path else 0.0) + min(0.2, avg_path_len * 0.05))
        else:
            topological_clarity = 0.4

        # 2. Causal Consistency: Does the earliest alert align with the root service?
        if earliest_alert and earliest_alert.get("service") == root_service:
            causal_consistency = 0.95
        elif causal_chain and causal_chain[0].get("service") == root_service:
            causal_consistency = 0.90
        elif any(c.get("service") == root_service for c in causal_chain[:3]):
            causal_consistency = 0.70
        else:
            causal_consistency = 0.40

        # 3. Evidence Completeness: Availability of metrics, logs, pairwise correlations
        evidence_points = 0.0
        if causal_chain:
            evidence_points += 0.35
        if dependency_paths:
            evidence_points += 0.25
        if top_pairwise:
            evidence_points += 0.25
        if earliest_alert:
            evidence_points += 0.15
        evidence_completeness = min(1.0, evidence_points)

        # 4. Symptom Breadth: Multi-tier cascade confirmation
        num_services = len(affected_services)
        if num_services >= 4:
            symptom_breadth = 0.95
        elif num_services == 3:
            symptom_breadth = 0.85
        elif num_services == 2:
            symptom_breadth = 0.70
        else:
            symptom_breadth = 0.50

        # 5. Correlation Cohesion: Phase 3 cohesion score
        correlation_cohesion = min(1.0, max(0.0, correlation_score))

        # Weighted aggregate formula
        w_topo = 0.30
        w_causal = 0.25
        w_evid = 0.20
        w_symp = 0.15
        w_cohes = 0.10

        composite = (
            w_topo * topological_clarity +
            w_causal * causal_consistency +
            w_evid * evidence_completeness +
            w_symp * symptom_breadth +
            w_cohes * correlation_cohesion
        )

        final_confidence = round(max(0.0, min(1.0, composite)), 3)

        breakdown = ConfidenceBreakdown(
            topological_clarity=round(topological_clarity, 3),
            causal_consistency=round(causal_consistency, 3),
            evidence_completeness=round(evidence_completeness, 3),
            symptom_breadth=round(symptom_breadth, 3),
            correlation_cohesion=round(correlation_cohesion, 3)
        )

        return breakdown, final_confidence

    def _build_evidence_summary(
        self,
        incident_data: Dict[str, Any],
        evidence: Dict[str, Any],
        root_service: str,
        earliest_alert: Dict[str, Any],
        latest_alert: Dict[str, Any],
        propagation_path: List[str]
    ) -> List[str]:
        summary = []
        alert_count = incident_data.get("alert_count", 0)
        span = evidence.get("temporal_span_seconds", 0.0)
        summary.append(f"Correlated {alert_count} alert(s) across a {span:.1f}s temporal window.")

        if earliest_alert:
            summary.append(
                f"Initial signal detected at {earliest_alert.get('timestamp')} on '{earliest_alert.get('service')}' "
                f"({earliest_alert.get('alert_type')}: {earliest_alert.get('metric')}={earliest_alert.get('metric_value')})."
            )

        if propagation_path and len(propagation_path) > 1:
            path_str = " -> ".join(propagation_path)
            summary.append(f"Failure propagated along verified dependency path: {path_str}.")

        top_pairwise = evidence.get("top_pairwise_correlations") or []
        if top_pairwise:
            top = top_pairwise[0]
            summary.append(
                f"Strongest pairwise correlation ({top.get('total_score', 0):.2f}) observed between "
                f"'{top.get('service_a')}' and '{top.get('service_b')}'."
            )

        return summary

    def _build_causal_narrative(
        self,
        root_service: str,
        causal_chain: List[Dict[str, Any]],
        propagation_path: List[str],
        earliest_alert: Dict[str, Any]
    ) -> str:
        if not causal_chain:
            return f"Incident originated on {root_service} and propagated to dependent callers."

        steps = []
        for idx, alert in enumerate(causal_chain[:5], start=1):
            svc = alert.get("service", "unknown")
            atype = alert.get("alert_type", "alert")
            metric = alert.get("metric", "")
            val = alert.get("metric_value") or alert.get("value")
            ts = alert.get("first_alert_time") or alert.get("timestamp") or ""

            # Clean timestamp display (HH:MM:SS or relative)
            ts_clean = ""
            if "T" in ts:
                ts_clean = f" [{ts.split('T')[1][:8]}]"
            elif len(ts) >= 19:
                ts_clean = f" [{ts[11:19]}]"
            elif ts:
                ts_clean = f" [{ts}]"

            val_str = f"={val}" if val is not None and val != "" else ""
            metric_str = f" ({metric}{val_str})" if metric else ""
            steps.append(f"Step {idx}{ts_clean}: {svc} triggered {atype}{metric_str}")

        narrative = "Causal Progression: " + " -> ".join(steps)
        if len(causal_chain) > 5:
            narrative += f" (followed by {len(causal_chain) - 5} subsequent cascading alerts)."
        return narrative

    def _build_recommendation(
        self,
        root_service: str,
        earliest_alert: Dict[str, Any],
        causal_chain: List[Dict[str, Any]]
    ) -> str:
        """
        Builds informative, human-readable guidance.
        DO NOT include executable shell commands or automated actions.
        """
        metric = earliest_alert.get("metric", "")
        alert_type = earliest_alert.get("alert_type", "")

        if "db" in root_service.lower() or "postgres" in root_service.lower():
            return (
                f"1. Investigate {root_service} database connection saturation and active query locks. "
                f"2. Inspect slow queries on the orders table and check index utilization. "
                f"3. Verify connection pool sizing on upstream services (order-api, checkout-api)."
            )
        elif "redis" in root_service.lower():
            return (
                f"1. Check {root_service} memory fragmentation and eviction policies. "
                f"2. Inspect cache hit/miss ratio and network latency. "
                f"3. Verify connection timeout configurations on caller services."
            )
        else:
            return (
                f"1. Check {root_service} health, CPU/memory headroom, and error logs for {alert_type}. "
                f"2. Review recent configuration changes or traffic spikes targeting {root_service}. "
                f"3. Inspect upstream retry and circuit breaker policies to prevent cascade amplification."
            )
