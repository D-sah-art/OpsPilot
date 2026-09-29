import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from .models import Alert
from .engine import telemetry_engine

def emit_alert(
    service: str,
    severity: str,
    alert_type: str,
    metric: str,
    metric_value: float,
    threshold: float,
    message: str,
    source: str = "shopflow-telemetry-agent",
    dependency: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    timestamp: Optional[str] = None
) -> Alert:
    alert = Alert(
        id=f"alt_{uuid.uuid4().hex[:10]}",
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        service=service,
        severity=severity.upper(),
        alert_type=alert_type,
        metric=metric,
        metric_value=metric_value,
        threshold=threshold,
        message=message,
        source=source,
        dependency=dependency,
        tags=tags or {}
    )
    telemetry_engine.record_alert(alert)
    return alert
