import time
import httpx
from fastapi.testclient import TestClient

# Real ShopFlow application
from services.api_gateway.main import app as shopflow_app
from chaos.engine import chaos_engine as shopflow_chaos

# OpsPilot application & components
from app.main import app as opspilot_app
from app.ingestion.adapter import ShopFlowAdapter
from app.ingestion.service import IngestionService
from app.database.repository import TelemetryRepository
from app.topology.graph import dependency_graph
from app.database.session import get_db
from app.models.service import Service
from app.models.alert import Alert

def test_health_independent_of_shopflow(client):
    """Verifies constraint 1: OpsPilot /health reports own status independently."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "opspilot-backend"
    assert "shopflow" in data

def test_end_to_end_shopflow_ingestion(db_session):
    """
    End-to-End Integration Test:
    1. Resets and triggers `database_cascade` in the REAL ShopFlow environment.
    2. Uses ShopFlowAdapter connected directly to the real ShopFlow ASGI app.
    3. Runs synchronization into OpsPilot SQLite database.
    4. Verifies exactly 29 alerts are ingested and stored.
    5. Verifies topology and dependency graph.
    6. Verifies raw payloads are preserved without any root-cause bias.
    7. Verifies idempotency / duplicate prevention on repeated sync.
    """
    # 1. Reset ShopFlow and trigger database_cascade
    shopflow_chaos.reset()
    shopflow_chaos.trigger_scenario("database_cascade")

    # Wait for ShopFlow cascade runner to emit all stages
    start_t = time.time()
    while time.time() - start_t < 15.0:
        st = shopflow_chaos.get_status()
        if st.get("state") == "COMPLETED" or st.get("alert_count", 0) >= 28:
            break
        time.sleep(0.3)

    # 2. Configure ShopFlowAdapter using TestClient against the real ShopFlow app
    adapter = ShopFlowAdapter(
        base_url="http://test-shopflow",
        client=TestClient(shopflow_app)
    )

    ingestion_svc = IngestionService(adapter=adapter)

    # 3. Perform Sync into OpsPilot SQLite
    sync_result = ingestion_svc.sync_shopflow(db=db_session)
    assert sync_result["status"] == "success"
    assert sync_result["connected"] is True
    assert sync_result["new_alerts"] == 29

    # 4. Verify stored alerts in SQLite
    stored_alerts = TelemetryRepository.get_alerts(db_session, limit=100)
    assert len(stored_alerts) == 29, f"Expected 29 stored alerts, got {len(stored_alerts)}"

    # Verify variety of alert types
    alert_types = set(a["alert_type"] for a in stored_alerts)
    assert len(alert_types) >= 8
    assert "DB_QUERY_SLOW" in alert_types
    assert "DB_CONNECTION_EXHAUSTION" in alert_types
    assert "DEPENDENCY_TIMEOUT" in alert_types
    assert "CHECKOUT_FAILURE" in alert_types
    assert "UPSTREAM_5XX_SURGE" in alert_types

    # 5. Verify no artificial root-cause diagnosis field is injected
    for alert in stored_alerts:
        assert "root_cause" not in alert
        assert "diagnosis" not in alert
        assert "cause" not in alert
        assert alert["raw_payload"] is not None

    # 6. Verify Topology loaded in NetworkX and DB
    nodes = dependency_graph.get_nodes()
    node_ids = [n["id"] for n in nodes]
    assert "postgresql" in node_ids
    assert "order-api" in node_ids
    assert "checkout-api" in node_ids
    assert "api-gateway" in node_ids
    assert "shopflow-frontend" in node_ids

    # Verify dependency paths exist
    path_gateway_to_pg = dependency_graph.get_path("api-gateway", "postgresql")
    assert path_gateway_to_pg is not None
    assert path_gateway_to_pg[0] == "api-gateway"
    assert path_gateway_to_pg[-1] == "postgresql"

    # 7. Verify Idempotency: Duplicate sync must NOT create duplicate alerts
    repeat_sync = ingestion_svc.sync_shopflow(db=db_session)
    assert repeat_sync["new_alerts"] == 0
    alerts_after_repeat = TelemetryRepository.get_alerts(db_session, limit=100)
    assert len(alerts_after_repeat) == 29

    # Clean up ShopFlow
    shopflow_chaos.reset()

def test_api_endpoints_with_ingested_data(client, db_session):
    """Verifies that OpsPilot REST API returns real ingested data."""
    # Seed a service and alert into db_session
    svc = TelemetryRepository.upsert_service(
        db_session,
        Service(service_id="postgresql", name="PostgreSQL DB", type="database", status="Operational")
    )
    alert = Alert(
        id="alt_api_test",
        timestamp="2026-09-05T00:00:00Z",
        service="postgresql",
        severity="CRITICAL",
        alert_type="DB_QUERY_SLOW",
        metric="db_latency_ms",
        metric_value=450.0,
        threshold=100.0,
        message="Slow query test",
        raw_payload={"test": True}
    )
    TelemetryRepository.save_alerts(db_session, [alert])

    # Test /api/services
    res_services = client.get("/api/services")
    assert res_services.status_code == 200
    services_data = res_services.json()
    assert len(services_data) >= 1
    assert any(s["service_id"] == "postgresql" for s in services_data)

    # Test /api/alerts
    res_alerts = client.get("/api/alerts")
    assert res_alerts.status_code == 200
    alerts_data = res_alerts.json()
    assert len(alerts_data) >= 1
    assert alerts_data[0]["id"] == "alt_api_test"
    assert alerts_data[0]["alert_type"] == "DB_QUERY_SLOW"

    # Test /api/topology
    res_topo = client.get("/api/topology")
    assert res_topo.status_code == 200
    assert "nodes" in res_topo.json()
