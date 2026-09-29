import networkx as nx
from typing import List, Dict, Any, Optional
from collections import Counter
from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from .models import CorrelationEvidence, PairwiseScore
from .scoring import parse_iso_timestamp

def build_correlation_evidence(
    cluster_alerts: List[Alert],
    pairwise_scores: List[PairwiseScore],
    graph: DependencyGraph
) -> CorrelationEvidence:
    """
    Constructs rich, inspectable correlation evidence for an incident cluster.
    """
    if not cluster_alerts:
        return CorrelationEvidence()

    # Sort cluster alerts deterministically by (timestamp, service, id)
    sorted_alerts = sorted(
        cluster_alerts,
        key=lambda a: (parse_iso_timestamp(a.timestamp), a.service, a.id)
    )

    earliest = sorted_alerts[0]
    latest = sorted_alerts[-1]
    t_min = parse_iso_timestamp(earliest.timestamp)
    t_max = parse_iso_timestamp(latest.timestamp)
    span = round(max(0.0, t_max - t_min), 2)

    # 1. Primary Affected Services
    seen_services = set()
    services_ordered = []
    for a in sorted_alerts:
        if a.service not in seen_services:
            seen_services.add(a.service)
            services_ordered.append(a.service)

    # 2. Causal Chronological Sequence (First alert per service)
    causal_chain = []
    service_first_seen = {}
    for a in sorted_alerts:
        if a.service not in service_first_seen:
            service_first_seen[a.service] = {
                "service": a.service,
                "first_alert_time": a.timestamp,
                "timestamp": a.timestamp,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "metric": a.metric,
                "metric_value": a.metric_value,
                "value": a.metric_value,
                "message": a.message
            }
            causal_chain.append(service_first_seen[a.service])

    # 3. Topology Dependency Paths
    # Gather directed dependency paths between pairs of services in the cluster
    dependency_paths = []
    seen_paths = set()
    for s1 in services_ordered:
        for s2 in services_ordered:
            if s1 != s2 and s1 in graph.graph and s2 in graph.graph:
                if nx.has_path(graph.graph, s1, s2):
                    p = nx.shortest_path(graph.graph, s1, s2)
                    p_tuple = tuple(p)
                    if p_tuple not in seen_paths:
                        seen_paths.add(p_tuple)
                        dependency_paths.append(p)

    # If no directed paths, search connected undirected paths
    if not dependency_paths:
        for s1 in services_ordered:
            for s2 in services_ordered:
                if s1 != s2:
                    p = graph.get_path(s1, s2)
                    if p and len(p) > 1:
                        p_tuple = tuple(p)
                        if p_tuple not in seen_paths:
                            seen_paths.add(p_tuple)
                            dependency_paths.append(p)

    # Sort paths by length descending
    dependency_paths.sort(key=lambda x: len(x), reverse=True)

    # 4. Breakdowns
    alert_type_counts = dict(Counter(a.alert_type for a in sorted_alerts))
    severity_counts = dict(Counter(a.severity.upper() for a in sorted_alerts))

    # 5. Top Pairwise Correlations
    # Filter pairwise scores that belong to this cluster
    cluster_alert_ids = set(a.id for a in cluster_alerts)
    relevant_scores = [
        s for s in pairwise_scores
        if s.alert_a_id in cluster_alert_ids and s.alert_b_id in cluster_alert_ids
    ]
    relevant_scores.sort(key=lambda s: s.total_score, reverse=True)

    top_links = []
    seen_pairs = set()
    for s in relevant_scores:
        pair_key = tuple(sorted([s.alert_a_id, s.alert_b_id]))
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            top_links.append({
                "alert_a_id": s.alert_a_id,
                "alert_b_id": s.alert_b_id,
                "service_a": s.service_a,
                "service_b": s.service_b,
                "score": s.total_score,
                "breakdown": {
                    "dependency": s.dependency_score,
                    "graph_distance": s.graph_distance_score,
                    "causal_order": s.causal_order_score,
                    "temporal": s.temporal_score,
                    "service": s.service_score,
                    "alert_type": s.alert_type_score,
                    "severity": s.severity_score,
                    "tag_and_metric": s.tag_and_metric_score
                },
                "reasons": s.reasons
            })
        if len(top_links) >= 15:
            break

    return CorrelationEvidence(
        temporal_span_seconds=span,
        earliest_alert={
            "id": earliest.id,
            "timestamp": earliest.timestamp,
            "service": earliest.service,
            "alert_type": earliest.alert_type,
            "severity": earliest.severity
        },
        latest_alert={
            "id": latest.id,
            "timestamp": latest.timestamp,
            "service": latest.service,
            "alert_type": latest.alert_type,
            "severity": latest.severity
        },
        dependency_paths=dependency_paths[:5],
        causal_chain=causal_chain,
        primary_affected_services=services_ordered,
        alert_type_breakdown=alert_type_counts,
        severity_breakdown=severity_counts,
        top_pairwise_correlations=top_links
    )
