import httpx
import pytest
from app.ingestion.adapter import ShopFlowAdapter

def test_adapter_connectivity_failure():
    # Points to non-existent port to test offline handling
    adapter = ShopFlowAdapter(base_url="http://localhost:59999", timeout=0.5)
    
    assert adapter.check_connectivity() is False
    assert adapter.fetch_topology() == {"nodes": [], "edges": []}
    assert adapter.fetch_health_summary() == {"status": "Unknown", "healthy_services": 0, "total_services": 0}
    assert adapter.fetch_alerts() == []
    assert adapter.fetch_logs() == []
    assert adapter.fetch_events() == []
    assert adapter.fetch_metrics() == {"services": {}}
    assert adapter.fetch_services() == {"services": {}}

def test_adapter_successful_mock():
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self):
            return self._json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("Mock error", request=None, response=None)

    class MockClient:
        def request(self, method: str, url: str, **kwargs):
            if url == "/health":
                return MockResponse({"status": "healthy"})
            elif url == "/api/topology":
                return MockResponse({"nodes": [{"id": "api-gateway"}], "edges": []})
            elif url == "/telemetry/alerts":
                return MockResponse([{"id": "alt_1", "service": "postgresql", "severity": "WARNING", "alert_type": "DB_QUERY_SLOW", "metric": "latency", "metric_value": 500, "threshold": 100, "message": "slow"}])
            elif url == "/telemetry/logs":
                return MockResponse([{"id": "log_1", "service": "api-gateway", "level": "INFO", "event": "TEST", "message": "msg"}])
            elif url == "/telemetry/metrics":
                return MockResponse({"services": {"postgresql": {"cpu_pct": 20.0}}})
            elif url == "/telemetry/events":
                return MockResponse([{"id": "evt_1", "service": "api-gateway", "event_type": "INIT", "description": "init"}])
            return MockResponse({}, status_code=404)

    adapter = ShopFlowAdapter(base_url="http://mock-shopflow:8000", client=MockClient())

    assert adapter.check_connectivity() is True
    assert len(adapter.fetch_topology()["nodes"]) == 1
    assert len(adapter.fetch_alerts()) == 1
    assert len(adapter.fetch_logs()) == 1
    assert "postgresql" in adapter.fetch_metrics()["services"]
    assert len(adapter.fetch_events()) == 1
