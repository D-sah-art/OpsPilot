import threading
import time
import random
from collections import deque
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .models import LogEntry, Alert, SystemEvent, ServiceMetrics

class TelemetryEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelemetryEngine, cls).__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self):
        self.log_buffer = deque(maxlen=2000)
        self.alert_buffer = deque(maxlen=1000)
        self.event_buffer = deque(maxlen=1000)
        self.services: Dict[str, ServiceMetrics] = {}
        self._mutex = threading.Lock()
        
        # Initialize default metrics for all 7 services
        service_names = [
            "api-gateway",
            "product-api",
            "order-api",
            "checkout-api",
            "auth-service",
            "postgresql",
            "redis"
        ]
        
        for s in service_names:
            self.services[s] = self._create_baseline_metrics(s)
            
        # Add initial system boot event
        self.record_event(SystemEvent(
            service="api-gateway",
            event_type="SYSTEM_INITIALIZED",
            description="ShopFlow telemetry system online. All microservices operational.",
            severity="INFO",
            payload={"version": "1.0.0", "status": "Operational"}
        ))

    def _create_baseline_metrics(self, service: str) -> ServiceMetrics:
        now = datetime.now(timezone.utc).isoformat()
        if service == "postgresql":
            return ServiceMetrics(
                service=service,
                timestamp=now,
                cpu_pct=15.2,
                memory_pct=42.0,
                request_rate_rps=120.0,
                latency_p50_ms=4.2,
                latency_p90_ms=8.5,
                latency_p99_ms=18.0,
                error_rate_pct=0.0,
                active_requests=5,
                db_connections_active=4,
                db_connections_idle=16,
                db_connections_max=20,
                db_latency_ms=4.2,
                db_error_count=0,
                availability_pct=99.99,
                status="Operational"
            )
        elif service == "redis":
            return ServiceMetrics(
                service=service,
                timestamp=now,
                cpu_pct=6.1,
                memory_pct=18.5,
                request_rate_rps=280.0,
                latency_p50_ms=0.8,
                latency_p90_ms=1.5,
                latency_p99_ms=3.2,
                error_rate_pct=0.0,
                active_requests=8,
                redis_latency_ms=0.8,
                redis_hits=850,
                redis_misses=24,
                availability_pct=100.0,
                status="Operational"
            )
        elif service == "api-gateway":
            return ServiceMetrics(
                service=service,
                timestamp=now,
                cpu_pct=18.4,
                memory_pct=31.2,
                request_rate_rps=65.0,
                latency_p50_ms=22.0,
                latency_p90_ms=48.0,
                latency_p99_ms=92.0,
                error_rate_pct=0.0,
                active_requests=12,
                availability_pct=100.0,
                status="Operational"
            )
        else:
            return ServiceMetrics(
                service=service,
                timestamp=now,
                cpu_pct=12.0 + random.uniform(0.5, 4.0),
                memory_pct=25.0 + random.uniform(1.0, 5.0),
                request_rate_rps=35.0,
                latency_p50_ms=15.0,
                latency_p90_ms=32.0,
                latency_p99_ms=65.0,
                error_rate_pct=0.0,
                active_requests=3,
                availability_pct=100.0,
                status="Operational"
            )

    def record_log(self, log_entry: LogEntry):
        with self._mutex:
            self.log_buffer.append(log_entry)

    def record_alert(self, alert: Alert):
        with self._mutex:
            self.alert_buffer.append(alert)

    def record_event(self, event: SystemEvent):
        with self._mutex:
            self.event_buffer.append(event)

    def update_metrics(self, service: str, **kwargs):
        with self._mutex:
            if service in self.services:
                current = self.services[service].model_dump()
                current.update(kwargs)
                current["timestamp"] = datetime.now(timezone.utc).isoformat()
                self.services[service] = ServiceMetrics(**current)

    def get_metrics(self) -> Dict[str, Any]:
        with self._mutex:
            # Add slight realistic micro-fluctuations to operational services
            now = datetime.now(timezone.utc).isoformat()
            result = {}
            for s_name, s_metric in self.services.items():
                m = s_metric.model_copy()
                m.timestamp = now
                if m.status == "Operational":
                    jitter = random.uniform(-0.5, 0.5)
                    m.cpu_pct = max(2.0, min(95.0, round(m.cpu_pct + jitter, 1)))
                result[s_name] = m.model_dump()
            return {
                "timestamp": now,
                "environment": "production-simulation",
                "services": result
            }

    def get_logs(
        self,
        limit: int = 100,
        service: Optional[str] = None,
        level: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._mutex:
            items = list(self.log_buffer)
            if service:
                items = [item for item in items if item.service == service]
            if level:
                items = [item for item in items if item.level.upper() == level.upper()]
            if search:
                s_lower = search.lower()
                items = [item for item in items if s_lower in item.message.lower() or s_lower in item.event.lower()]
            return [item.model_dump() for item in items[-limit:]][::-1]

    def get_alerts(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
        service: Optional[str] = None,
        alert_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._mutex:
            items = list(self.alert_buffer)
            if severity:
                items = [item for item in items if item.severity.upper() == severity.upper()]
            if service:
                items = [item for item in items if item.service == service]
            if alert_type:
                items = [item for item in items if item.alert_type == alert_type]
            return [item.model_dump() for item in items[-limit:]][::-1]

    def get_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._mutex:
            items = list(self.event_buffer)
            if event_type:
                items = [item for item in items if item.event_type == event_type]
            if service:
                items = [item for item in items if item.service == service]
            return [item.model_dump() for item in items[-limit:]][::-1]

    def get_services(self) -> Dict[str, Any]:
        with self._mutex:
            services_info = {}
            for name, metric in self.services.items():
                services_info[name] = {
                    "service": name,
                    "status": metric.status,
                    "availability_pct": metric.availability_pct,
                    "latency_ms": metric.latency_p50_ms,
                    "error_rate_pct": metric.error_rate_pct,
                    "cpu_pct": metric.cpu_pct,
                    "memory_pct": metric.memory_pct,
                    "updated_at": metric.timestamp
                }
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": services_info
            }

    def get_health_summary(self) -> Dict[str, Any]:
        with self._mutex:
            statuses = [s.status for s in self.services.values()]
            if "Major Outage" in statuses:
                overall = "Major Outage"
            elif "Degraded" in statuses:
                overall = "Degraded"
            elif "Recovering" in statuses:
                overall = "Recovering"
            else:
                overall = "Operational"

            active_alerts_count = len([a for a in self.alert_buffer])
            critical_alerts = len([a for a in self.alert_buffer if a.severity == "CRITICAL"])
            warning_alerts = len([a for a in self.alert_buffer if a.severity == "WARNING"])

            return {
                "status": overall,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "healthy_services": len([s for s in statuses if s == "Operational"]),
                "total_services": len(self.services),
                "active_alerts_total": active_alerts_count,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "services": {k: v.status for k, v in self.services.items()}
            }

    def reset(self):
        with self._mutex:
            service_names = list(self.services.keys())
            for s in service_names:
                self.services[s] = self._create_baseline_metrics(s)
            self.alert_buffer.clear()
            self.event_buffer.append(SystemEvent(
                service="api-gateway",
                event_type="TELEMETRY_RESET",
                description="Telemetry buffers and metrics restored to clean baseline.",
                severity="INFO",
                payload={"status": "Operational"}
            ))

# Global telemetry engine singleton
telemetry_engine = TelemetryEngine()
