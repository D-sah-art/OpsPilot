from typing import List, Dict, Any
from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from .base import CorrelationStrategy
from ..models import Incident, CorrelationEvidence, PairwiseScore
from ..scoring import parse_iso_timestamp, compute_temporal_score
from ..clustering import determine_max_severity, generate_deterministic_incident_id
from ..evidence import build_correlation_evidence

class TimeOnlyStrategy(CorrelationStrategy):
    """
    Baseline correlation strategy that groups alerts purely based on temporal proximity.
    Ignores service relationships, topology paths, graph distance, and causal direction.
    """
    @property
    def name(self) -> str:
        return "time_only"

    def correlate(
        self,
        alerts: List[Alert],
        graph: DependencyGraph,
        time_window_seconds: float = 45.0,
        threshold: float = 0.5
    ) -> List[Incident]:
        if not alerts:
            return []

        # Sort alerts deterministically by timestamp
        sorted_alerts = sorted(
            alerts,
            key=lambda a: (parse_iso_timestamp(a.timestamp), a.id)
        )

        clusters: List[List[Alert]] = []
        current_cluster: List[Alert] = []
        last_timestamp = None

        for alert in sorted_alerts:
            t = parse_iso_timestamp(alert.timestamp)
            if last_timestamp is None:
                current_cluster.append(alert)
                last_timestamp = t
            elif (t - last_timestamp) <= time_window_seconds:
                current_cluster.append(alert)
                last_timestamp = t
            else:
                clusters.append(current_cluster)
                current_cluster = [alert]
                last_timestamp = t

        if current_cluster:
            clusters.append(current_cluster)

        incidents = []
        for cluster in clusters:
            cluster_alert_ids = [a.id for a in cluster]
            affected_svcs = list(dict.fromkeys(a.service for a in cluster))
            max_severity = determine_max_severity(cluster)
            incident_id = generate_deterministic_incident_id(cluster_alert_ids, self.name)

            if len(affected_svcs) == 1:
                title = f"{affected_svcs[0]} alert cluster ({len(cluster)} alerts)"
            else:
                title = f"Temporal alert cluster across {', '.join(affected_svcs[:3])} ({len(cluster)} alerts)"

            # Build pairwise temporal scores
            pairwise_scores = []
            for i in range(len(cluster)):
                for j in range(i + 1, len(cluster)):
                    t_i = parse_iso_timestamp(cluster[i].timestamp)
                    t_j = parse_iso_timestamp(cluster[j].timestamp)
                    s_temp, r_temp = compute_temporal_score(abs(t_i - t_j))
                    pairwise_scores.append(PairwiseScore(
                        alert_a_id=cluster[i].id,
                        alert_b_id=cluster[j].id,
                        service_a=cluster[i].service,
                        service_b=cluster[j].service,
                        total_score=s_temp,
                        dependency_score=0.0,
                        graph_distance_score=0.0,
                        causal_order_score=0.0,
                        temporal_score=s_temp,
                        service_score=1.0 if cluster[i].service == cluster[j].service else 0.0,
                        alert_type_score=0.5,
                        severity_score=0.5,
                        tag_and_metric_score=0.5,
                        reasons=[r_temp]
                    ))

            evidence = build_correlation_evidence(cluster, pairwise_scores, graph)

            # Average score based purely on temporal proximity
            avg_score = round(
                sum(ps.total_score for ps in pairwise_scores) / len(pairwise_scores), 4
            ) if pairwise_scores else 1.0

            incident = Incident(
                incident_id=incident_id,
                title=title,
                severity=max_severity,
                status="OPEN",
                created_at=cluster[0].timestamp,
                updated_at=cluster[-1].timestamp,
                alert_count=len(cluster),
                alert_ids=cluster_alert_ids,
                affected_services=affected_svcs,
                correlation_score=avg_score,
                correlation_method=self.name,
                correlation_evidence=evidence
            )
            incidents.append(incident)

        return incidents
