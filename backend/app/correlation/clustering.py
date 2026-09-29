import hashlib
import networkx as nx
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from .models import Incident, CorrelationEvidence, PairwiseScore
from .scoring import parse_iso_timestamp
from .evidence import build_correlation_evidence

SEVERITY_RANK = {
    "CRITICAL": 3,
    "WARNING": 2,
    "WARN": 2,
    "INFO": 1
}

def determine_max_severity(alerts: List[Alert]) -> str:
    max_rank = 0
    max_sev = "INFO"
    for a in alerts:
        sev = (a.severity or "INFO").upper()
        rank = SEVERITY_RANK.get(sev, 1)
        if rank > max_rank:
            max_rank = rank
            max_sev = sev
    return max_sev

def generate_deterministic_incident_id(alert_ids: List[str], method: str) -> str:
    """Generates a deterministic incident ID from sorted alert IDs and method."""
    combined = f"{method}:" + ",".join(sorted(alert_ids))
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:10]
    return f"inc_{digest}"

def cluster_alerts_into_incidents(
    alerts: List[Alert],
    pairwise_scores: List[PairwiseScore],
    threshold: float,
    graph: DependencyGraph,
    method: str = "dependency_aware"
) -> List[Incident]:
    """
    Deterministically clusters alerts into incidents using graph connected components.
    """
    if not alerts:
        return []

    # Deterministic alert sorting by (timestamp, service, id)
    sorted_alerts = sorted(
        alerts,
        key=lambda a: (parse_iso_timestamp(a.timestamp), a.service, a.id)
    )
    alert_map = {a.id: a for a in sorted_alerts}

    # Build correlation graph
    corr_graph = nx.Graph()
    for a in sorted_alerts:
        corr_graph.add_node(a.id)

    # Add edges for pairwise scores >= threshold
    pair_score_map = {}
    for ps in pairwise_scores:
        pair_key = (ps.alert_a_id, ps.alert_b_id)
        pair_score_map[pair_key] = ps.total_score
        pair_score_map[(ps.alert_b_id, ps.alert_a_id)] = ps.total_score
        if ps.total_score >= threshold:
            corr_graph.add_edge(ps.alert_a_id, ps.alert_b_id, weight=ps.total_score)

    # Find connected components (clusters)
    components = list(nx.connected_components(corr_graph))

    # Sort components deterministically by earliest alert timestamp
    def component_sort_key(comp):
        comp_alerts = [alert_map[aid] for aid in comp if aid in alert_map]
        if not comp_alerts:
            return (0.0, "")
        earliest = min(comp_alerts, key=lambda a: (parse_iso_timestamp(a.timestamp), a.id))
        return (parse_iso_timestamp(earliest.timestamp), earliest.id)

    sorted_components = sorted(components, key=component_sort_key)

    incidents = []
    for comp in sorted_components:
        comp_alerts = [alert_map[aid] for aid in comp if aid in alert_map]
        if not comp_alerts:
            continue

        comp_alerts.sort(key=lambda a: (parse_iso_timestamp(a.timestamp), a.service, a.id))
        comp_alert_ids = [a.id for a in comp_alerts]

        # Affected services ordered by first alert appearance
        seen_svcs = set()
        affected_services = []
        for a in comp_alerts:
            if a.service not in seen_svcs:
                seen_svcs.add(a.service)
                affected_services.append(a.service)

        # Average correlation score in cluster
        if len(comp_alerts) > 1:
            edge_scores = []
            for i in range(len(comp_alerts)):
                for j in range(i + 1, len(comp_alerts)):
                    aid1 = comp_alerts[i].id
                    aid2 = comp_alerts[j].id
                    score = pair_score_map.get((aid1, aid2))
                    if score is not None and score >= threshold:
                        edge_scores.append(score)
            avg_score = round(sum(edge_scores) / len(edge_scores), 4) if edge_scores else threshold
        else:
            avg_score = 1.0

        incident_id = generate_deterministic_incident_id(comp_alert_ids, method)
        max_severity = determine_max_severity(comp_alerts)

        # Build descriptive title
        if len(affected_services) == 1:
            title = f"{affected_services[0]} degradation ({len(comp_alerts)} alerts)"
        else:
            svc_summary = ", ".join(affected_services[:3])
            if len(affected_services) > 3:
                svc_summary += f" +{len(affected_services) - 3} more"
            title = f"Cascade failure across {svc_summary} ({len(comp_alerts)} alerts)"

        # Evidence
        evidence = build_correlation_evidence(comp_alerts, pairwise_scores, graph)

        incident = Incident(
            incident_id=incident_id,
            title=title,
            severity=max_severity,
            status="OPEN",
            created_at=comp_alerts[0].timestamp,
            updated_at=comp_alerts[-1].timestamp,
            alert_count=len(comp_alerts),
            alert_ids=comp_alert_ids,
            affected_services=affected_services,
            correlation_score=avg_score,
            correlation_method=method,
            correlation_evidence=evidence
        )
        incidents.append(incident)

    return incidents
