from telemetry.models import LogEntry, Alert, SystemEvent
from telemetry.engine import telemetry_engine

def test_telemetry_metrics(client):
    res = client.get("/telemetry/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data
    assert "postgresql" in data["services"]
    assert "api-gateway" in data["services"]
    pg_metrics = data["services"]["postgresql"]
    assert "db_connections_active" in pg_metrics
    assert "db_latency_ms" in pg_metrics
    assert "cpu_pct" in pg_metrics

def test_telemetry_logs(client):
    # Trigger a request to generate a log
    client.get("/api/products")
    res = client.get("/telemetry/logs?limit=50")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    first_log = logs[0]
    assert "timestamp" in first_log
    assert "service" in first_log
    assert "level" in first_log
    assert "event" in first_log

def test_telemetry_alerts(client):
    # Manually record an alert and verify
    telemetry_engine.record_alert(Alert(
        service="postgresql",
        severity="WARNING",
        alert_type="DB_QUERY_SLOW",
        metric="db_latency_ms",
        metric_value=450.0,
        threshold=100.0,
        message="Slow query detected"
    ))
    res = client.get("/telemetry/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0
    assert alerts[0]["alert_type"] == "DB_QUERY_SLOW"
    assert alerts[0]["severity"] == "WARNING"

def test_telemetry_events(client):
    res = client.get("/telemetry/events")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)

def test_telemetry_services(client):
    res = client.get("/telemetry/services")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data
    assert "postgresql" in data["services"]
    assert data["services"]["postgresql"]["status"] == "Operational"
