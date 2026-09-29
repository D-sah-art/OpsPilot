import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.models import Alert, Metric, LogEvent, SystemEvent, Service, Dependency

logger = logging.getLogger("opspilot.telemetry_normalizer")

class TelemetryNormalizer:

    @staticmethod
    def normalize_alert(raw: Dict[str, Any]) -> Optional[Alert]:
        try:
            return Alert(
                id=raw.get("id") or f"alt_{hash(f'{raw.get('timestamp')}_{raw.get('service')}_{raw.get('alert_type')}')}",
                timestamp=raw.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                service=raw.get("service", "unknown"),
                severity=raw.get("severity", "WARNING").upper(),
                alert_type=raw.get("alert_type", "GENERIC_ALERT"),
                metric=raw.get("metric", "unknown"),
                metric_value=float(raw.get("metric_value", 0.0)),
                threshold=float(raw.get("threshold", 0.0)),
                message=raw.get("message", ""),
                source=raw.get("source", "shopflow-telemetry-agent"),
                dependency=raw.get("dependency"),
                tags=raw.get("tags") or {},
                raw_payload=raw
            )
        except Exception as e:
            logger.error(f"Failed to normalize alert: {e}. Raw payload: {raw}")
            return None

    @staticmethod
    def normalize_log(raw: Dict[str, Any]) -> Optional[LogEvent]:
        try:
            return LogEvent(
                id=raw.get("id") or f"log_{hash(f'{raw.get('timestamp')}_{raw.get('service')}_{raw.get('event')}')}",
                timestamp=raw.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                service=raw.get("service", "unknown"),
                level=raw.get("level", "INFO").upper(),
                event=raw.get("event", "GENERIC_EVENT"),
                message=raw.get("message", ""),
                request_id=raw.get("request_id"),
                dependency=raw.get("dependency"),
                latency_ms=float(raw["latency_ms"]) if raw.get("latency_ms") is not None else None,
                status_code=int(raw["status_code"]) if raw.get("status_code") is not None else None,
                metadata=raw.get("metadata") or {},
                raw_payload=raw
            )
        except Exception as e:
            logger.error(f"Failed to normalize log: {e}. Raw payload: {raw}")
            return None

    @staticmethod
    def normalize_metrics_snapshot(raw_metrics_root: Dict[str, Any]) -> List[Metric]:
        """
        Unpacks ShopFlow metrics snapshot dictionary { "timestamp": ..., "services": { "postgresql": {...}, ... } }
        into a flat list of discrete Metric models.
        """
        metrics = []
        ts = raw_metrics_root.get("timestamp") or datetime.now(timezone.utc).isoformat()
        services_dict = raw_metrics_root.get("services", {})

        for svc_name, svc_metrics in services_dict.items():
            if not isinstance(svc_metrics, dict):
                continue

            for key, val in svc_metrics.items():
                if key in ["service", "timestamp", "status", "http_status_counts"]:
                    continue
                if isinstance(val, (int, float)):
                    # Determine unit
                    unit = None
                    if "pct" in key:
                        unit = "%"
                    elif "ms" in key or "latency" in key:
                        unit = "ms"
                    elif "rps" in key:
                        unit = "req/s"
                    elif "count" in key or "hits" in key or "misses" in key:
                        unit = "count"

                    metrics.append(Metric(
                        timestamp=svc_metrics.get("timestamp", ts),
                        service=svc_name,
                        metric_name=key,
                        value=float(val),
                        unit=unit,
                        tags={"service": svc_name, "status": svc_metrics.get("status", "Operational")},
                        raw_payload={key: val, "service": svc_name}
                    ))

        return metrics

    @staticmethod
    def normalize_event(raw: Dict[str, Any]) -> Optional[SystemEvent]:
        try:
            return SystemEvent(
                id=raw.get("id") or f"evt_{hash(f'{raw.get('timestamp')}_{raw.get('service')}_{raw.get('event_type')}')}",
                timestamp=raw.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                service=raw.get("service", "unknown"),
                event_type=raw.get("event_type", "GENERIC_EVENT"),
                message=raw.get("description") or raw.get("message", ""),
                metadata=raw.get("payload") or raw.get("metadata") or {},
                raw_payload=raw
            )
        except Exception as e:
            logger.error(f"Failed to normalize system event: {e}. Raw payload: {raw}")
            return None

    @staticmethod
    def normalize_service(raw: Dict[str, Any]) -> Optional[Service]:
        try:
            svc_id = raw.get("id") or raw.get("service_id") or raw.get("service")
            if not svc_id:
                return None
            return Service(
                service_id=svc_id,
                name=raw.get("name", svc_id),
                type=raw.get("type", "service"),
                status=raw.get("live_status") or raw.get("status", "Operational"),
                metadata={k: v for k, v in raw.items() if k not in ["id", "service_id", "name", "type", "status", "live_status"]}
            )
        except Exception as e:
            logger.error(f"Failed to normalize service: {e}. Raw payload: {raw}")
            return None

    @staticmethod
    def normalize_dependency(raw: Dict[str, Any]) -> Optional[Dependency]:
        try:
            src = raw.get("source")
            tgt = raw.get("target")
            if not src or not tgt:
                return None
            return Dependency(
                source=src,
                target=tgt,
                relationship=raw.get("type") or raw.get("protocol") or "calls",
                metadata={k: v for k, v in raw.items() if k not in ["source", "target", "type"]}
            )
        except Exception as e:
            logger.error(f"Failed to normalize dependency: {e}. Raw payload: {raw}")
            return None
