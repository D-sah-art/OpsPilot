import time
import pytest
from fastapi.testclient import TestClient

# Real ShopFlow application
from services.api_gateway.main import app as shopflow_app
from chaos.engine import chaos_engine as shopflow_chaos

# OpsPilot application & components
from app.main import app as opspilot_app
from app.ingestion.adapter import ShopFlowAdapter
from app.ingestion.service import IngestionService
from app.database.repository import TelemetryRepository
from app.correlation.service import correlation_service
from app.models.alert import Alert

def test_real_database_cascade_correlation_end_to_end(client, db_session):
    """
    End-to-End Test:
    1. Triggers REAL database_cascade in ShopFlow testbed.
    2. Ingests all 29 raw alerts into OpsPilot SQLite.
    3. Executes Dependency-Aware Correlation.
    4. Validates that all 29 alerts are unified into exactly 1 coherent incident.
    5. Validates that inspectable correlation evidence exposes the full dependency path and causal chain.
    6. Validates REST API endpoints (/api/incidents, /api/correlation/benchmark).
    7. Validates that an unrelated alert is cleanly separated into a distinct incident.
    """
    # 1. Reset ShopFlow and trigger real database_cascade
    shopflow_chaos.reset()
    TelemetryRepository.clear_all(db_session)
    shopflow_chaos.trigger_scenario("database_cascade")

    # Wait for ShopFlow cascade runner to complete
    start_t = time.time()
    while time.time() - start_t < 15.0:
        st = shopflow_chaos.get_status()
        if st.get("state") == "COMPLETED" or st.get("alert_count", 0) >= 28:
            break
        time.sleep(0.3)

    # 2. Ingest into OpsPilot SQLite
    adapter = ShopFlowAdapter(
        base_url="http://test-shopflow",
        client=TestClient(shopflow_app)
    )
    ingestion_svc = IngestionService(adapter=adapter)
    sync_res = ingestion_svc.sync_shopflow(db=db_session)

    assert sync_res["status"] == "success"
    assert sync_res["new_alerts"] == 29

    stored_alerts = TelemetryRepository.get_alerts(db_session, limit=100)
    assert len(stored_alerts) == 29, f"Expected 29 alerts, got {len(stored_alerts)}"

    # 3. Run Dependency-Aware Correlation via Service
    incidents = correlation_service.correlate_from_db(
        db=db_session,
        strategy_name="dependency_aware",
        persist=True
    )

    # 4. Verify exactly 1 incident generated from 29 alerts
    assert len(incidents) == 1, f"Expected exactly 1 incident, got {len(incidents)}"
    incident = incidents[0]

    assert incident.alert_count == 29
    assert len(incident.alert_ids) == 29
    assert incident.correlation_method == "dependency_aware"
    assert incident.severity == "CRITICAL"
    assert incident.status == "OPEN"

    # Verify all cascade services are in affected_services
    affected_set = set(incident.affected_services)
    assert "postgresql" in affected_set
    assert "order-api" in affected_set
    assert "checkout-api" in affected_set
    assert "api-gateway" in affected_set

    # 5. Verify Correlation Evidence
    evidence = incident.correlation_evidence
    assert evidence.temporal_span_seconds > 0.0
    assert len(evidence.primary_affected_services) >= 4
    
    # Verify Causal Chain: postgresql degraded first
    assert len(evidence.causal_chain) >= 4
    assert evidence.causal_chain[0]["service"] == "postgresql"
    assert evidence.causal_chain[0]["alert_type"] in ["DB_QUERY_SLOW", "DB_LOCK_CONTENTION"]

    # Verify Topological Path in evidence
    paths = evidence.dependency_paths
    assert len(paths) >= 1
    # Check that a directed path exists covering api-gateway downstream to postgresql
    full_path_found = any(
        ("api-gateway" in p and "postgresql" in p and p.index("api-gateway") < p.index("postgresql"))
        for p in paths
    )
    assert full_path_found, f"Expected path from api-gateway to postgresql in evidence paths: {paths}"

    # 6. Verify REST API Endpoints
    # GET /api/incidents
    res_list = client.get("/api/incidents")
    assert res_list.status_code == 200
    inc_list = res_list.json()
    assert len(inc_list) == 1
    assert inc_list[0]["incident_id"] == incident.incident_id
    assert inc_list[0]["alert_count"] == 29

    # GET /api/incidents/{incident_id}
    res_single = client.get(f"/api/incidents/{incident.incident_id}")
    assert res_single.status_code == 200
    inc_detail = res_single.json()
    assert inc_detail["incident_id"] == incident.incident_id
    assert len(inc_detail["alerts"]) == 29
    assert "correlation_evidence" in inc_detail
    assert inc_detail["correlation_evidence"]["causal_chain"][0]["service"] == "postgresql"

    # GET /api/correlation/benchmark
    res_bench = client.get("/api/correlation/benchmark")
    assert res_bench.status_code == 200
    bench_data = res_bench.json()
    assert bench_data["total_alerts"] == 29
    assert "dependency_aware" in bench_data["benchmark"]
    assert "time_only" in bench_data["benchmark"]
    assert bench_data["benchmark"]["dependency_aware"]["incidents_count"] == 1
    assert bench_data["benchmark"]["dependency_aware"]["alerts_grouped"] == 29

    # 7. Test Unrelated Alert Separation
    # Add an unrelated alert on external-payment-provider at the same timestamp
    unrelated_alert = Alert(
        id="alt_external_unrelated",
        timestamp=stored_alerts[0]["timestamp"],
        service="external-payment-provider",
        severity="WARNING",
        alert_type="WEBHOOK_LATENCY",
        metric="webhook_response_time",
        metric_value=2500.0,
        threshold=500.0,
        message="Payment webhook delivery latency elevated",
        raw_payload={"scenario": "unrelated_external"}
    )
    TelemetryRepository.save_alerts(db_session, [unrelated_alert])

    # Re-run dependency-aware: should produce 2 incidents (cascade incident + external service incident)
    incidents_with_unrelated = correlation_service.correlate_from_db(
        db=db_session,
        strategy_name="dependency_aware",
        persist=False
    )
    assert len(incidents_with_unrelated) == 2
    cascade_inc = next(i for i in incidents_with_unrelated if "postgresql" in i.affected_services)
    external_inc = next(i for i in incidents_with_unrelated if "external-payment-provider" in i.affected_services)
    assert cascade_inc.alert_count == 29
    assert external_inc.alert_count == 1
    assert "external-payment-provider" not in cascade_inc.affected_services

    # Time-only baseline: falsely merges the unrelated alert into the same incident
    time_only_incidents = correlation_service.correlate_from_db(
        db=db_session,
        strategy_name="time_only",
        time_window_seconds=45.0,
        persist=False
    )
    # Because external-payment-provider occurred at the same timestamp, time-only groups it with the cascade
    has_false_merge = any(
        "external-payment-provider" in i.affected_services and "postgresql" in i.affected_services
        for i in time_only_incidents
    )
    assert has_false_merge, "Time-only baseline should falsely merge unrelated alert occurring within window"

    # Clean up ShopFlow
    shopflow_chaos.reset()
