import pytest
from app.database.repository import TelemetryRepository
from app.remediation.service import RemediationService
from app.remediation.models import RemediationRequest, SafetyDecision, ExecutionStatus

@pytest.fixture
def mock_audit_incident(db_session):
    incident_data = {
        "incident_id": "inc_aud_1",
        "title": "Audit Test Incident",
        "severity": "CRITICAL",
        "status": "OPEN",
        "started_at": "2026-09-04T12:00:00Z",
        "alert_count": 3,
        "alert_ids": ["alt_a1"],
        "affected_services": ["checkout-api"],
        "correlation_score": 0.92
    }
    TelemetryRepository.save_incidents(db_session, [incident_data])
    TelemetryRepository.save_incident_diagnosis(db_session, "inc_aud_1", {
        "root_cause_service": "checkout-api",
        "confidence_score": 0.88,
        "recommended_action": "Restart checkout-api"
    })
    return "inc_aud_1"

def test_audit_trail_created_on_remediation(db_session, mock_audit_incident):
    svc = RemediationService()
    req = RemediationRequest(
        action="restart_service",
        target_service="checkout-api",
        mode="SIMULATION",
        requested_by="sre-agent-1"
    )

    result = svc.remediate_incident(db=db_session, incident_id=mock_audit_incident, request=req)
    assert result.decision == SafetyDecision.APPROVED
    assert result.execution_status == ExecutionStatus.SIMULATED_SUCCESS
    assert result.audit_id.startswith("aud_")

    # Verify audit record persisted in SQLite
    audits = TelemetryRepository.get_audits_for_incident(db_session, incident_id=mock_audit_incident)
    assert len(audits) >= 1
    record = audits[0]
    assert record["audit_id"] == result.audit_id
    assert record["incident_id"] == mock_audit_incident
    assert record["action"] == "restart_service"
    assert record["target_service"] == "checkout-api"
    assert record["decision"] == "APPROVED"
    assert record["actor"] == "sre-agent-1"
    assert "conditions" in record["details"]

def test_rejected_action_generates_audit_record(db_session, mock_audit_incident):
    svc = RemediationService()
    # Disallowed action
    req = RemediationRequest(
        action="unsupported_action",
        target_service="checkout-api",
        requested_by="operator-2"
    )

    result = svc.remediate_incident(db=db_session, incident_id=mock_audit_incident, request=req)
    assert result.decision in [SafetyDecision.REJECTED, SafetyDecision.HUMAN_REVIEW]
    assert result.execution_status == ExecutionStatus.SKIPPED

    # Audit must record the rejection/human review
    audits = TelemetryRepository.get_audits_for_incident(db_session, incident_id=mock_audit_incident)
    assert len(audits) >= 1
    rec = audits[0]
    assert rec["decision"] in ["REJECTED", "HUMAN_REVIEW"]
    assert rec["actor"] == "operator-2"

def test_audit_immutability(db_session, mock_audit_incident):
    # Ensure audit records accumulate and previous records remain untouched
    svc = RemediationService()
    req1 = RemediationRequest(action="restart_service", target_service="checkout-api", force=True)
    res1 = svc.remediate_incident(db=db_session, incident_id=mock_audit_incident, request=req1)

    req2 = RemediationRequest(action="reset_connections", target_service="checkout-api", force=True)
    res2 = svc.remediate_incident(db=db_session, incident_id=mock_audit_incident, request=req2)

    audits = TelemetryRepository.get_audits_for_incident(db_session, incident_id=mock_audit_incident)
    assert len(audits) == 2
    audit_ids = [a["audit_id"] for a in audits]
    assert res1.audit_id in audit_ids
    assert res2.audit_id in audit_ids
