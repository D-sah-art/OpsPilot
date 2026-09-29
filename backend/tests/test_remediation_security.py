import pytest
from app.database.repository import TelemetryRepository
from app.remediation.safety_gate import RemediationSafetyGate
from app.remediation.executor import RemediationExecutor
from app.remediation.models import ExecutionMode, ExecutionStatus

@pytest.fixture
def mock_security_incident(db_session):
    incident_data = {
        "incident_id": "inc_sec_1",
        "title": "Security Test Incident",
        "severity": "CRITICAL",
        "status": "OPEN",
        "started_at": "2026-09-04T12:00:00Z",
        "alert_count": 2,
        "alert_ids": ["alt_sec_1"],
        "affected_services": ["order-api"],
        "correlation_score": 0.95
    }
    TelemetryRepository.save_incidents(db_session, [incident_data])
    TelemetryRepository.save_incident_diagnosis(db_session, "inc_sec_1", {
        "root_cause_service": "order-api",
        "confidence_score": 0.90
    })
    return "inc_sec_1"

def test_command_injection_patterns_rejected(db_session, mock_security_incident):
    gate = RemediationSafetyGate()

    # Attempt shell command injection in parameter
    malicious_params = [
        {"grace_period_seconds": "10; sudo rm -rf /"},
        {"grace_period_seconds": "$(docker kill order-api)"},
        {"grace_period_seconds": "`kubectl delete pod`"},
        {"custom_cmd": "systemctl restart order-api"}
    ]

    for params in malicious_params:
        result = gate.evaluate(
            db=db_session,
            incident_id=mock_security_incident,
            action="restart_service",
            target_service="order-api",
            parameters=params
        )
        assert result.allowed is False
        assert "Security violation" in result.reason or "Unrecognized parameter" in result.reason or "must be an integer" in result.reason

def test_executor_never_executes_arbitrary_commands():
    executor = RemediationExecutor()

    # Attempting to call an arbitrary action string fails gracefully without running any subprocess
    status, reason, details = executor.execute(
        action="rm_rf_all",
        target_service="order-api",
        mode=ExecutionMode.SIMULATION
    )
    assert status == ExecutionStatus.FAILED
    assert "Unsupported remediation action" in reason

def test_simulation_mode_is_isolated():
    executor = RemediationExecutor()
    status, reason, details = executor.execute(
        action="restart_service",
        target_service="order-api",
        mode=ExecutionMode.SIMULATION,
        parameters={"grace_period_seconds": 5}
    )
    assert status == ExecutionStatus.SIMULATED_SUCCESS
    assert "[SIMULATION]" in reason
    assert "Host and processes were untouched" in reason
    assert details["mode"] == "SIMULATION"
