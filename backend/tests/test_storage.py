from app.database.repository import TelemetryRepository
from app.models import Alert, Metric, LogEvent, SystemEvent, Service, Dependency

def test_service_storage_and_upsert(db_session):
    svc1 = Service(
        service_id="order-api",
        name="Order API",
        type="service",
        status="Operational",
        metadata={"port": 8002}
    )
    TelemetryRepository.upsert_service(db_session, svc1)
    
    services = TelemetryRepository.get_services(db_session)
    assert len(services) == 1
    assert services[0]["service_id"] == "order-api"
    assert services[0]["status"] == "Operational"

    # Upsert with status update
    svc1_updated = Service(
        service_id="order-api",
        name="Order API",
        type="service",
        status="Degraded",
        metadata={"port": 8002}
    )
    TelemetryRepository.upsert_service(db_session, svc1_updated)
    
    services_after = TelemetryRepository.get_services(db_session)
    assert len(services_after) == 1
    assert services_after[0]["status"] == "Degraded"

def test_dependency_storage(db_session):
    dep = Dependency(
        source="checkout-api",
        target="order-api",
        relationship="HTTP/REST",
        metadata={"criticality": "critical"}
    )
    TelemetryRepository.upsert_dependency(db_session, dep)
    
    deps = TelemetryRepository.get_dependencies(db_session)
    assert len(deps) == 1
    assert deps[0]["source"] == "checkout-api"
    assert deps[0]["target"] == "order-api"

def test_alert_storage_and_deduplication(db_session):
    alert1 = Alert(
        id="alt_unique_01",
        timestamp="2026-09-05T00:01:00Z",
        service="postgresql",
        severity="WARNING",
        alert_type="DB_QUERY_SLOW",
        metric="query_duration_p95_ms",
        metric_value=450.0,
        threshold=100.0,
        message="Slow query on table orders",
        raw_payload={"raw": 1}
    )
    alert2 = Alert(
        id="alt_unique_02",
        timestamp="2026-09-05T00:02:00Z",
        service="postgresql",
        severity="CRITICAL",
        alert_type="DB_CONNECTION_EXHAUSTION",
        metric="connection_pool_active_pct",
        metric_value=98.0,
        threshold=90.0,
        message="Pool exhausted",
        raw_payload={"raw": 2}
    )

    # First insert
    count1 = TelemetryRepository.save_alerts(db_session, [alert1, alert2])
    assert count1 == 2

    # Second insert with same alerts (must be deduplicated!)
    count2 = TelemetryRepository.save_alerts(db_session, [alert1, alert2])
    assert count2 == 0

    # Retrieve alerts
    stored = TelemetryRepository.get_alerts(db_session)
    assert len(stored) == 2
    assert stored[0]["id"] in ["alt_unique_01", "alt_unique_02"]

def test_metrics_storage(db_session):
    metric1 = Metric(
        timestamp="2026-09-05T00:01:00Z",
        service="api-gateway",
        metric_name="latency_p50_ms",
        value=22.5,
        unit="ms"
    )
    metric2 = Metric(
        timestamp="2026-09-05T00:01:00Z",
        service="api-gateway",
        metric_name="error_rate_pct",
        value=0.0,
        unit="%"
    )
    count = TelemetryRepository.save_metrics(db_session, [metric1, metric2])
    assert count == 2

    stored = TelemetryRepository.get_metrics(db_session, service="api-gateway")
    assert len(stored) == 2

def test_logs_storage_and_deduplication(db_session):
    log1 = LogEvent(
        id="log_001",
        timestamp="2026-09-05T00:01:00Z",
        service="product-api",
        level="INFO",
        event="CACHE_HIT",
        message="Served 12 products from Redis",
        latency_ms=1.2,
        status_code=200
    )
    count1 = TelemetryRepository.save_logs(db_session, [log1])
    assert count1 == 1

    # Repeat insert
    count2 = TelemetryRepository.save_logs(db_session, [log1])
    assert count2 == 0

    stored = TelemetryRepository.get_logs(db_session, service="product-api")
    assert len(stored) == 1
    assert stored[0]["id"] == "log_001"

def test_events_storage_and_deduplication(db_session):
    ev1 = SystemEvent(
        id="evt_001",
        timestamp="2026-09-05T00:01:00Z",
        service="api-gateway",
        event_type="SYSTEM_INITIALIZED",
        message="System online"
    )
    count1 = TelemetryRepository.save_events(db_session, [ev1])
    assert count1 == 1

    # Repeat insert
    count2 = TelemetryRepository.save_events(db_session, [ev1])
    assert count2 == 0

    stored = TelemetryRepository.get_events(db_session)
    assert len(stored) == 1
    assert stored[0]["id"] == "evt_001"
