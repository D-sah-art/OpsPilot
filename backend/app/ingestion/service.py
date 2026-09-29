import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from .adapter import ShopFlowAdapter, shopflow_adapter
from .normalizer import TelemetryNormalizer
from app.database.repository import TelemetryRepository
from app.topology.graph import dependency_graph

from app.topology.discovery import topology_discovery_engine

logger = logging.getLogger("opspilot.ingestion_service")

class IngestionService:
    def __init__(self, adapter: Optional[ShopFlowAdapter] = None):
        self.adapter = adapter or shopflow_adapter

    def sync_shopflow(self, db: Session) -> Dict[str, Any]:
        """
        Executes a full synchronization pass with the external ShopFlow target.
        Ingests topology, services, alerts, logs, metrics, and events.
        Deduplicates records so repeated calls are idempotent.
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting ShopFlow telemetry synchronization from {self.adapter.base_url}")

        # 1. Check connectivity
        is_connected = self.adapter.check_connectivity()
        if not is_connected:
            logger.warning(f"ShopFlow target at {self.adapter.base_url} is unreachable")
            return {
                "status": "warning",
                "message": "ShopFlow target is unreachable",
                "connected": False,
                "timestamp": start_time.isoformat(),
                "new_alerts": 0,
                "new_logs": 0,
                "new_metrics": 0,
                "new_events": 0,
                "services_count": len(TelemetryRepository.get_services(db)),
                "edges_count": len(TelemetryRepository.get_dependencies(db))
            }

        # 2. Fetch raw telemetry from target environment
        raw_topology = self.adapter.fetch_topology()
        raw_alerts = self.adapter.fetch_alerts(limit=500)
        raw_logs = self.adapter.fetch_logs(limit=500)
        raw_metrics = self.adapter.fetch_metrics()
        raw_events = self.adapter.fetch_events(limit=500)
        raw_health_summary = self.adapter.fetch_health_summary()

        # 3. Dynamic Topology Discovery from observed telemetry & optional Grafana
        discovery_result = topology_discovery_engine.discover_from_sync(
            fallback_topology=raw_topology,
            logs=raw_logs,
            alerts=raw_alerts,
            metrics=raw_metrics,
            health_data=raw_health_summary,
            events=raw_events
        )

        nodes = discovery_result.nodes
        edges = discovery_result.edges

        # Update Database Services & Dependencies
        for node_dict in nodes:
            service_obj = TelemetryNormalizer.normalize_service(node_dict)
            if service_obj:
                TelemetryRepository.upsert_service(db, service_obj)

        for edge_dict in edges:
            dep_obj = TelemetryNormalizer.normalize_dependency(edge_dict)
            if dep_obj:
                TelemetryRepository.upsert_dependency(db, dep_obj)

        # 4. Ingest and Deduplicate Alerts
        normalized_alerts = []
        for a_dict in raw_alerts:
            a_obj = TelemetryNormalizer.normalize_alert(a_dict)
            if a_obj:
                normalized_alerts.append(a_obj)
        new_alerts_count = TelemetryRepository.save_alerts(db, normalized_alerts)

        # 5. Ingest and Deduplicate Logs
        normalized_logs = []
        for l_dict in raw_logs:
            l_obj = TelemetryNormalizer.normalize_log(l_dict)
            if l_obj:
                normalized_logs.append(l_obj)
        new_logs_count = TelemetryRepository.save_logs(db, normalized_logs)

        # 6. Ingest Metrics
        normalized_metrics = TelemetryNormalizer.normalize_metrics_snapshot(raw_metrics)
        new_metrics_count = TelemetryRepository.save_metrics(db, normalized_metrics)

        # 7. Ingest and Deduplicate Events
        normalized_events = []
        for e_dict in raw_events:
            e_obj = TelemetryNormalizer.normalize_event(e_dict)
            if e_obj:
                normalized_events.append(e_obj)
        new_events_count = TelemetryRepository.save_events(db, normalized_events)

        logger.info(
            f"ShopFlow sync completed: {new_alerts_count} new alerts, {new_logs_count} new logs, "
            f"{new_metrics_count} new metrics, {new_events_count} new events. "
            f"Topology: {len(nodes)} nodes, {len(edges)} edges ({discovery_result.source})"
        )

        return {
            "status": "success",
            "message": "ShopFlow telemetry synchronized successfully",
            "connected": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "new_alerts": new_alerts_count,
            "total_alerts_in_batch": len(raw_alerts),
            "new_logs": new_logs_count,
            "new_metrics": new_metrics_count,
            "new_events": new_events_count,
            "services_count": len(nodes),
            "edges_count": len(edges),
            "discovery_source": discovery_result.discovery_source,
            "discovery_mode": discovery_result.source,
            "grafana_connected": discovery_result.grafana_connected
        }

ingestion_service = IngestionService()
