import pytest
from app.database.repository import TelemetryRepository
from app.remediation.safety_gate import RemediationSafetyGate
from app.remediation.models import SafetyDecision, ExecutionMode

@pytest.fixture
def mock_open_incident(db_session):
    incident_data = {
        "incident_id": "inc_gate_test_1",
        "title": "Order Service Degradation",
        "severity": "CRITICAL",
        "status": "OPEN",
        "started_at": "2026-09-04T12:00:00Z",
        "alert_count": 5,
        "alert_ids": ["alt_1", "alt_2"],
        "affected_services": ["order-api", "checkout-api"],
        "correlation_score": 0.95,
        "correlation_evidence": {}
    }
    TelemetryRepository.save_incidents(db_session, [incident_data])
    
    # Save diagnosis with high confidence
    diagnosis_data = {
        "incident_id": "inc_gate_test_1",
        "root_cause_service": "order-api",
        "root_cause_summary": "Order API worker thread deadlock",
        "confidence_score": 0.90,
        "confidence_breakdown": {
            "topological_clarity": 0.9,
            "causal_consistency": 0.9,
            "evidence_completeness": 0.9,
            "symptom_breadth": 0.9,
            "correlation_cohesion": 0.95
        },
        "causal_narrative": "Order API deadlocked -> checkout API 504",
        "propagation_path": ["order-api", "checkout-api"],
        "evidence_summary": ["Earliest alert on order-api"],
        "recommended_action": "Restart order-api service instances."
    }
    TelemetryRepository.save_incident_diagnosis(db_session, "inc_gate_test_1", diagnosis_data)
    return "inc_gate_test_1"

def test_safety_gate_approves_valid_request(db_session, mock_open_incident):
    gate = RemediationSafetyGate()
    result = gate.evaluate(
        db=db_session,
        incident_id=mock_open_incident,
        action="restart_service",
        target_service="order-api",
        mode="SIMULATION",
        parameters={"grace_period_seconds": 10}
    )

    assert result.allowed is True
    assert result.decision == SafetyDecision.APPROVED
    assert result.action == "restart_service"
    assert result.target_service == "order-api"
    assert len(result.conditions) == 10
    assert all(c.passed for c in result.conditions)

def test_safety_gate_rejects_missing_incident(db_session):
    gate = RemediationSafetyGate()
    result = gate.evaluate(
        db=db_session,
        incident_id="non_existent_inc",
        action="restart_service",
        target_service="order-api"
    )

    assert result.allowed is False
    assert result.decision == SafetyDecision.REJECTED
    assert "not found" in result.reason

def test_safety_gate_routes_to_human_review_for_disallowed_target(db_session, mock_open_incident):
    # Attempting to restart postgresql which is not in restart_service allowed_services
    gate = RemediationSafetyGate()
    result = gate.evaluate(
        db=db_session,
        incident_id=mock_open_incident,
        action="restart_service",
        target_service="postgresql"
    )

    assert result.allowed is False
    assert result.decision == SafetyDecision.HUMAN_REVIEW
    assert "not permitted for action 'restart_service'" in result.reason

def test_safety_gate_routes_to_human_review_for_low_confidence(db_session, mock_open_incident):
    # Update diagnosis to low confidence
    low_conf_diagnosis = {
        "root_cause_service": "order-api",
        "confidence_score": 0.45  # Below policy threshold of 0.70
    }
    TelemetryRepository.save_incident_diagnosis(db_session, mock_open_incident, low_conf_diagnosis)

    gate = RemediationSafetyGate()
    result = gate.evaluate(
        db=db_session,
        incident_id=mock_open_incident,
        action="restart_service",
        target_service="order-api"
    )

    assert result.allowed is False
    assert result.decision == SafetyDecision.HUMAN_REVIEW
    assert "below policy minimum" in result.reason

def test_safety_gate_rejects_non_actionable_state(db_session, mock_open_incident):
    # Mark incident as RESOLVED
    TelemetryRepository.update_incident_status(db_session, mock_open_incident, status="RESOLVED")

    gate = RemediationSafetyGate()
    result = gate.evaluate(
        db=db_session,
        incident_id=mock_open_incident,
        action="restart_service",
        target_service="order-api"
    )

    assert result.allowed is False
    assert result.decision == SafetyDecision.HUMAN_REVIEW
    assert "not in actionable state" in result.reason
