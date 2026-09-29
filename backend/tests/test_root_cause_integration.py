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
from app.root_cause.service import root_cause_service
from app.root_cause.models import RootCauseAnalysis

def test_real_database_cascade_root_cause_end_to_end(client, db_session):
    """
    End-to-End Integration Test for Phase 4:
    1. Triggers REAL database_cascade in ShopFlow testbed (29 alerts).
    2. Syncs all 29 alerts into OpsPilot SQLite.
    3. Runs Phase 3 correlation (exactly 1 incident).
    4. Diagnoses root cause via Phase 4 engine.
    5. Validates that postgresql is identified as the root cause.
    6. Validates evidence-derived confidence score and breakdown.
    7. Validates causal propagation path and safe recommendations.
    8. Validates REST API endpoints and SQLite persistence/caching.
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

    # 3. Run Phase 3 Correlation and persist incident
    incidents = correlation_service.correlate_from_db(
        db=db_session,
        strategy_name="dependency_aware",
        persist=True
    )
    assert len(incidents) == 1
    incident = incidents[0]
    incident_id = incident.incident_id

    # 4. Diagnose Root Cause via POST /api/incidents/{incident_id}/root-cause
    response = client.post(f"/api/incidents/{incident_id}/root-cause", json={"force_refresh": True})
    assert response.status_code == 200
    diagnosis = response.json()

    # 5. Verify Root Cause is PostgreSQL
    assert diagnosis["root_cause_service"] == "postgresql"
    assert diagnosis["incident_id"] == incident_id
    assert "postgresql" in diagnosis["root_cause_summary"].lower()

    # 6. Verify Evidence-Derived Confidence
    conf = diagnosis["confidence_score"]
    assert 0.0 <= conf <= 1.0
    breakdown = diagnosis["confidence_breakdown"]
    assert 0.0 <= breakdown["topological_clarity"] <= 1.0
    assert 0.0 <= breakdown["causal_consistency"] <= 1.0
    assert 0.0 <= breakdown["evidence_completeness"] <= 1.0
    assert 0.0 <= breakdown["symptom_breadth"] <= 1.0
    assert 0.0 <= breakdown["correlation_cohesion"] <= 1.0
    assert breakdown["causal_consistency"] >= 0.8  # postgresql triggered first

    # 7. Verify Causal Propagation Path
    prop_path = diagnosis["propagation_path"]
    assert len(prop_path) >= 2
    assert "postgresql" in prop_path
    assert "order-api" in prop_path or "checkout-api" in prop_path

    # Verify Evidence Summary
    assert len(diagnosis["evidence_summary"]) >= 2

    # Verify Safe Informational Recommendation (No executable commands)
    rec = diagnosis["recommended_action"]
    assert len(rec) > 10
    assert "sudo" not in rec
    assert "systemctl" not in rec
    assert "docker" not in rec
    assert "kill" not in rec
    assert "rm" not in rec

    # 8. Verify SQLite Persistence & Caching
    # GET /api/incidents/{incident_id}/root-cause
    get_res = client.get(f"/api/incidents/{incident_id}/root-cause")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["root_cause_service"] == "postgresql"
    assert get_data["diagnosed_at"] == diagnosis["diagnosed_at"]

    # Verify incident GET endpoint includes updated root_cause_service and diagnosis
    inc_res = client.get(f"/api/incidents/{incident_id}")
    assert inc_res.status_code == 200
    inc_data = inc_res.json()
    assert inc_data["root_cause_service"] == "postgresql"
    assert "diagnosis" in inc_data
    assert inc_data["diagnosis"]["root_cause_service"] == "postgresql"

    # Reset ShopFlow
    shopflow_chaos.reset()
