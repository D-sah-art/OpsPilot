import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.topology.graph import dependency_graph, DependencyGraph
from app.database.repository import TelemetryRepository
from .models import Incident, CorrelationBenchmarkResult
from .strategies.base import CorrelationStrategy
from .strategies.time_only import TimeOnlyStrategy
from .strategies.dependency_aware import DependencyAwareStrategy

logger = logging.getLogger("opspilot.correlation.service")

class CorrelationService:
    def __init__(self, graph: Optional[DependencyGraph] = None):
        self.graph = graph or dependency_graph
        self.strategies: Dict[str, CorrelationStrategy] = {
            "dependency_aware": DependencyAwareStrategy(),
            "time_only": TimeOnlyStrategy()
        }

    def get_strategy(self, name: str) -> CorrelationStrategy:
        strategy = self.strategies.get(name)
        if not strategy:
            logger.warning(f"Unknown correlation strategy '{name}', falling back to 'dependency_aware'")
            strategy = self.strategies["dependency_aware"]
        return strategy

    def correlate_alerts(
        self,
        alerts: List[Alert],
        strategy_name: str = "dependency_aware",
        time_window_seconds: float = 600.0,
        threshold: float = 0.45,
        persist: bool = False,
        db: Optional[Session] = None
    ) -> List[Incident]:
        """
        Executes correlation on provided alerts using specified strategy.
        Optionally persists generated incidents into SQLite database.
        """
        strategy = self.get_strategy(strategy_name)
        incidents = strategy.correlate(
            alerts=alerts,
            graph=self.graph,
            time_window_seconds=time_window_seconds,
            threshold=threshold
        )

        if persist and db is not None:
            TelemetryRepository.delete_incidents(db)
            saved_count = TelemetryRepository.save_incidents(db, incidents)
            logger.info(f"Persisted {saved_count} incident(s) into SQLite database")

        return incidents

    def correlate_from_db(
        self,
        db: Session,
        strategy_name: str = "dependency_aware",
        time_window_seconds: float = 600.0,
        threshold: float = 0.45,
        persist: bool = True
    ) -> List[Incident]:
        """
        Loads all stored alerts from DB and runs correlation.
        """
        raw_alerts = TelemetryRepository.get_alerts(db, limit=1000)
        alerts = [
            Alert(
                id=a["id"],
                timestamp=a["timestamp"],
                service=a["service"],
                severity=a["severity"],
                alert_type=a["alert_type"],
                metric=a["metric"],
                metric_value=a["metric_value"],
                threshold=a["threshold"],
                message=a["message"],
                source=a.get("source", "shopflow-telemetry-agent"),
                dependency=a.get("dependency"),
                tags=a.get("tags", {}),
                raw_payload=a.get("raw_payload", {})
            )
            for a in raw_alerts
        ]
        return self.correlate_alerts(
            alerts=alerts,
            strategy_name=strategy_name,
            time_window_seconds=time_window_seconds,
            threshold=threshold,
            persist=persist,
            db=db
        )

    def run_benchmark(self, alerts: List[Alert]) -> Dict[str, CorrelationBenchmarkResult]:
        """
        Runs both Time-Only and Dependency-Aware strategies against identical alerts
        and compares execution time, incident counts, cohesion, and grouping quality.
        """
        results = {}

        for name, strategy in self.strategies.items():
            start_t = time.perf_counter()
            incidents = strategy.correlate(
                alerts=alerts,
                graph=self.graph,
                time_window_seconds=600.0 if name == "dependency_aware" else 45.0,
                threshold=0.45
            )
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 3)

            total_alerts = len(alerts)
            incidents_count = len(incidents)
            alerts_grouped = sum(inc.alert_count for inc in incidents)
            isolated_incidents = sum(1 for inc in incidents if inc.alert_count == 1)
            
            avg_size = round(alerts_grouped / incidents_count, 2) if incidents_count > 0 else 0.0
            avg_cohesion = round(
                sum(inc.correlation_score for inc in incidents) / incidents_count, 4
            ) if incidents_count > 0 else 0.0

            # Count separated unrelated services
            unrelated_separated = 0
            if incidents_count > 1:
                unrelated_separated = sum(1 for inc in incidents if len(inc.affected_services) == 1)

            if name == "dependency_aware":
                summary = (
                    f"Dependency-Aware strategy grouped {alerts_grouped}/{total_alerts} alerts into "
                    f"{incidents_count} incident(s) with average cohesion {avg_cohesion:.2f} based on "
                    f"NetworkX topology and causal direction."
                )
            else:
                summary = (
                    f"Time-Only baseline grouped {alerts_grouped}/{total_alerts} alerts into "
                    f"{incidents_count} incident(s) using a fixed sliding time window without topology."
                )

            results[name] = CorrelationBenchmarkResult(
                strategy=name,
                total_alerts=total_alerts,
                incidents_count=incidents_count,
                alerts_grouped=alerts_grouped,
                isolated_incidents=isolated_incidents,
                average_incident_size=avg_size,
                average_cohesion_score=avg_cohesion,
                unrelated_alerts_separated=unrelated_separated,
                execution_time_ms=elapsed_ms,
                summary=summary,
                incidents=incidents
            )

        return results

# Default singleton correlation service instance
correlation_service = CorrelationService()
