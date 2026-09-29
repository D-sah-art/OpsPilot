import pytest
from pydantic import ValidationError
from app.models import Alert, Metric, LogEvent, SystemEvent, Service, Dependency

def test_valid_alert_creation():
    alert = Alert(
        id="alt_test123",
        timestamp="2026-09-05T00:00:00Z",
        service="postgresql",
        severity="CRITICAL",
        alert_type="DB_CONNECTION_EXHAUSTION",
        metric="connection_pool_active_pct",
        metric_value=98.0,
        threshold=90.0,
        message="PostgreSQL connection pool near saturation",
        source="shopflow-telemetry-agent",
        dependency=None,
        tags={"pool": "primary"},
        raw_payload={"original_id": "alt_test123", "nested": "data"}
    )
    assert alert.id == "alt_test123"
    assert alert.service == "postgresql"
    assert alert.severity == "CRITICAL"
    assert alert.metric_value == 98.0
    assert alert.raw_payload["original_id"] == "alt_test123"
    assert not hasattr(alert, "root_cause")
    assert not hasattr(alert, "diagnosis")

def test_invalid_alert_validation():
    with pytest.raises(ValidationError):
        # Missing required field 'service' or wrong type for metric_value
        Alert(
            id="alt_invalid",
            timestamp="2026-09-05T00:00:00Z",
            severity="HIGH",
            alert_type="TEST",
            metric="cpu",
            metric_value="not-a-number",  # Invalid type
            threshold=50.0,
            message="Test message"
        )

def test_metric_validation():
    metric = Metric(
        timestamp="2026-09-05T00:00:00Z",
        service="order-api",
        metric_name="latency_p95_ms",
        value=3200.0,
        unit="ms",
        tags={"route": "/orders"},
        raw_payload={"raw": True}
    )
    assert metric.service == "order-api"
    assert metric.value == 3200.0
    assert metric.unit == "ms"

def test_log_event_validation():
    log = LogEvent(
        id="log_test123",
        timestamp="2026-09-05T00:00:00Z",
        service="checkout-api",
        level="ERROR",
        event="DEPENDENCY_TIMEOUT",
        message="Call to order-api timed out after 3000ms",
        request_id="req_987",
        dependency="order-api",
        latency_ms=3000.0,
        status_code=504,
        metadata={"attempts": 3},
        raw_payload={"raw_log": "entry"}
    )
    assert log.service == "checkout-api"
    assert log.status_code == 504
    assert log.dependency == "order-api"

def test_system_event_validation():
    event = SystemEvent(
        id="evt_test123",
        timestamp="2026-09-05T00:00:00Z",
        service="api-gateway",
        event_type="SCENARIO_STARTED",
        message="Chaos scenario database_cascade triggered",
        metadata={"scenario_id": "database_cascade"},
        raw_payload={"full": "event"}
    )
    assert event.service == "api-gateway"
    assert event.event_type == "SCENARIO_STARTED"

def test_service_and_dependency_models():
    svc = Service(
        service_id="postgresql",
        name="PostgreSQL Database",
        type="database",
        status="Operational",
        metadata={"port": 5432}
    )
    assert svc.service_id == "postgresql"
    assert svc.status == "Operational"

    dep = Dependency(
        source="checkout-api",
        target="order-api",
        relationship="HTTP/REST",
        metadata={"criticality": "critical"}
    )
    assert dep.source == "checkout-api"
    assert dep.target == "order-api"
