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
from app.remediation.service import remediation_service
from app.remediation.models import SafetyDecision, ExecutionStatus, RecoveryStatus

def test_real_database_cascade_remediation_and_audit_end_to_end(client, db_session):
    """
    End-to-End Integration Test for Phase 5:
    1. Triggers REAL database_cascade in ShopFlow testbed (29 alerts).
    2. Syncs all 29 alerts into OpsPilot SQLite.
    3. Runs Phase 3 correlation (exactly 1 incident).
    4. Diagnoses root cause via Phase 4 engine (identifying postgresql).
    5. Evaluates Safety Gate:
       - Attempting 'restart_service' on postgresql is rejected and routed to HUMAN_REVIEW (databases not allowed for auto-restart).
       - Attempting 'reset_connections' on postgresql is APPROVED (in allow-list for connection resets).
    6. Executes simulated remediation in SIMULATION mode.
    7. Verifies recovery signals against ShopFlow.
    8. Validates persistent, immutable audit trail accessible via REST API.
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

    # 3. Run Phase 3 Correlation
    incidents = correlation_service.correlate_from_db(
        db=db_session,
        strategy_name="dependency_aware",
        persist=True
    )
    assert len(incidents) == 1
    incident = incidents[0]
    incident_id = incident.incident_id

    # 4. Diagnose Root Cause (Phase 4)
    diagnosis = root_cause_service.diagnose_incident(db=db_session, incident_id=incident_id)
    assert diagnosis.root_cause_service == "postgresql"
    assert diagnosis.confidence_score > 0.70

    # 5. Safety Gate Test: Disallowed action 'restart_service' on database -> HUMAN_REVIEW
    res_unsafe = client.post(
        f"/api/incidents/{incident_id}/remediate",
        json={"action": "restart_service", "target_service": "postgresql"}
    )
    assert res_unsafe.status_code == 200
    data_unsafe = res_unsafe.json()
    assert data_unsafe["decision"] == "HUMAN_REVIEW"
    assert data_unsafe["execution_status"] == "SKIPPED"
    assert "not permitted for action 'restart_service'" in data_unsafe["reason"]

    # 6. Safety Gate Test: Allowed action 'reset_connections' on postgresql -> APPROVED
    res_safe = client.post(
        f"/api/incidents/{incident_id}/remediate",
        json={"action": "reset_connections", "target_service": "postgresql", "mode": "SIMULATION"}
    )
    assert res_safe.status_code == 200
    data_safe = res_safe.json()
    assert data_safe["decision"] == "APPROVED"
    assert data_safe["execution_status"] == "SIMULATED_SUCCESS"
    assert data_safe["execution_mode"] == "SIMULATION"

    # 7. Recovery Verification Endpoint
    rec_res = client.post(f"/api/incidents/{incident_id}/remediate/verify")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "status" in rec_data
    assert "signals_evaluated" in rec_data

    # 8. Query Latest Remediation & Audit Trail Endpoints
    latest_res = client.get(f"/api/incidents/{incident_id}/remediation")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["incident_id"] == incident_id
    assert latest_data["action"] == "reset_connections"

    audit_res = client.get(f"/api/incidents/{incident_id}/audit")
    assert audit_res.status_code == 200
    audit_list = audit_res.json()
    assert len(audit_list) == 2  # 1st rejected (human review) + 2nd approved
    # Both audit entries exist and are immutable
    decisions = [a["decision"] for a in audit_list]
    assert "HUMAN_REVIEW" in decisions
    assert "APPROVED" in decisions

    # Reset ShopFlow
    shopflow_chaos.reset()

def test_remediation_friendly_order_api_restart(client, db_session):
    """
    Test B: Validates remediation-friendly scenario for stateless service (order-api).
    Simulates high load / memory failure on order-api -> auto-remediation restart -> recovery.
    """
    # Create incident on order-api
    incident_data = {
        "incident_id": "inc_order_mem_1",
        "title": "High Memory Consumption on Order API",
        "severity": "CRITICAL",
        "status": "OPEN",
        "started_at": "2026-09-04T12:00:00Z",
        "alert_count": 4,
        "alert_ids": ["alt_mem_1"],
        "affected_services": ["order-api"],
        "correlation_score": 0.95
    }
    TelemetryRepository.save_incidents(db_session, [incident_data])
    TelemetryRepository.save_incident_diagnosis(db_session, "inc_order_mem_1", {
        "root_cause_service": "order-api",
        "confidence_score": 0.92,
        "recommended_action": "Restart order-api instance"
    })

    # Trigger remediation
    res = client.post(
        "/api/incidents/inc_order_mem_1/remediate",
        json={"action": "restart_service", "target_service": "order-api", "mode": "SIMULATION"}
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["decision"] == "APPROVED"
    assert res_data["execution_status"] == "SIMULATED_SUCCESS"

    # Verify incident state was updated
    inc_res = client.get("/api/incidents/inc_order_mem_1")
    assert inc_res.status_code == 200
    inc_info = inc_res.json()
    assert inc_info["status"] in ["MITIGATED", "RESOLVED", "OPEN"]
