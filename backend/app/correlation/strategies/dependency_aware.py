import logging
from typing import List
from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from .base import CorrelationStrategy
from ..models import Incident, PairwiseScore
from ..scoring import calculate_pairwise_score, parse_iso_timestamp
from ..clustering import cluster_alerts_into_incidents

logger = logging.getLogger("opspilot.correlation.dependency_aware")

class DependencyAwareStrategy(CorrelationStrategy):
    """
    Production-grade, deterministic, explainable correlation strategy that combines
    topology, graph distance, causal propagation direction, temporal proximity,
    alert types, severity, and telemetry metadata.
    """
    @property
    def name(self) -> str:
        return "dependency_aware"

    def correlate(
        self,
        alerts: List[Alert],
        graph: DependencyGraph,
        time_window_seconds: float = 600.0,
        threshold: float = 0.45
    ) -> List[Incident]:
        if not alerts:
            return []

        # Sort alerts deterministically by timestamp, service, and id
        sorted_alerts = sorted(
            alerts,
            key=lambda a: (parse_iso_timestamp(a.timestamp), a.service, a.id)
        )

        pairwise_scores: List[PairwiseScore] = []

        # Compute pairwise scores for pairs within maximum time window
        n = len(sorted_alerts)
        for i in range(n):
            a_i = sorted_alerts[i]
            t_i = parse_iso_timestamp(a_i.timestamp)
            for j in range(i + 1, n):
                a_j = sorted_alerts[j]
                t_j = parse_iso_timestamp(a_j.timestamp)
                
                # If beyond maximum time window, stop checking forward
                if (t_j - t_i) > time_window_seconds:
                    break

                ps = calculate_pairwise_score(a_i, a_j, graph)
                pairwise_scores.append(ps)

        # Cluster into incidents using graph connected components
        incidents = cluster_alerts_into_incidents(
            alerts=sorted_alerts,
            pairwise_scores=pairwise_scores,
            threshold=threshold,
            graph=graph,
            method=self.name
        )

        logger.info(
            f"DependencyAwareStrategy: correlated {len(alerts)} alerts into {len(incidents)} incident(s) "
            f"(threshold={threshold})"
        )

        return incidents
