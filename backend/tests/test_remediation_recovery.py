import pytest
from unittest.mock import MagicMock
from app.models.alert import Alert
from app.models.metric import Metric
from app.database.repository import TelemetryRepository
from app.remediation.recovery import RecoveryVerifier
from app.remediation.models import RecoveryStatus, RemediationRequest
from app.remediation.service import RemediationService

def test_recovery_verifier_complete_recovery(db_session):
    """
    Test 1: Complete Recovery.
    All signals available and positive:
    - Health endpoint healthy
    - No critical alerts
    - Nominal metrics
    - Active checkout probe succeeds
    -> Status: RECOVERED
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {
        "status": "healthy",
        "services": {
            "order-api": {"status": "Operational"}
        }
    }
    mock_adapter.probe_checkout.return_value = {
        "success": True,
        "status_code": 200,
        "latency_ms": 42.5,
        "order_id": "ord_rec_complete_1",
        "error": None
    }

    # Add nominal metric
    nominal_metric = Metric(
        id="met_rec_1",
        timestamp="2026-09-04T12:00:00Z",
        service="order-api",
        metric_name="error_rate",
        value=0.01,
        unit="ratio"
    )
    TelemetryRepository.save_metrics(db_session, [nominal_metric])

    verifier = RecoveryVerifier(adapter=mock_adapter)
    evidence = verifier.verify(
        db=db_session,
        incident_id="inc_rec_comp",
        target_service="order-api",
        action="restart_service"
    )

    assert evidence.status == RecoveryStatus.RECOVERED
    assert evidence.healthy is True
    assert evidence.checkout_successful is True
    assert evidence.active_alerts_count == 0
    assert evidence.error_rate == 0.01

def test_recovery_verifier_healthy_target_with_active_incident_alerts(db_session):
    """
    Test 2: Target /health is healthy, but active critical alerts remain for incident.
    Must NOT return RECOVERED -> Must return NOT_RECOVERED.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {
        "status": "healthy",
        "services": {
            "order-api": {"status": "Operational"}
        }
    }
    mock_adapter.probe_checkout.return_value = {
        "success": True,
        "status_code": 200,
        "latency_ms": 35.0,
        "order_id": "ord_probe_1",
        "error": None
    }

    # Add active critical alert for order-api
    crit_alert = Alert(
        id="alt_rec_crit_incident",
        timestamp="2026-09-04T12:00:00Z",
        service="order-api",
        severity="CRITICAL",
        alert_type="HIGH_ERROR_RATE",
        metric="error_rate",
        metric_value=0.55,
        threshold=0.05,
        message="Order API critical error rate"
    )
    TelemetryRepository.save_alerts(db_session, [crit_alert])

    verifier = RecoveryVerifier(adapter=mock_adapter)
    evidence = verifier.verify(
        db=db_session,
        incident_id="inc_with_crit_alerts",
        target_service="order-api",
        action="restart_service"
    )

    # Active critical alert must block RECOVERED
    assert evidence.status == RecoveryStatus.NOT_RECOVERED
    assert evidence.healthy is False
    assert evidence.active_alerts_count >= 1

def test_recovery_verifier_missing_metrics_with_independent_signals(db_session):
    """
    Test 3: Missing Metrics.
    No metrics in DB, but health is healthy + active checkout probe succeeds + 0 alerts.
    -> Sufficient independent signals allow RECOVERED without fabricated metrics.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {
        "status": "healthy",
        "services": {
            "checkout-api": {"status": "Operational"}
        }
    }
    mock_adapter.probe_checkout.return_value = {
        "success": True,
        "status_code": 200,
        "latency_ms": 50.0,
        "order_id": "ord_probe_no_metrics",
        "error": None
    }

    verifier = RecoveryVerifier(adapter=mock_adapter)
    evidence = verifier.verify(
        db=db_session,
        incident_id="inc_no_metrics",
        target_service="checkout-api",
        action="restart_service"
    )

    assert evidence.status == RecoveryStatus.RECOVERED
    assert evidence.healthy is True
    assert evidence.error_rate is None  # Never fabricated!
    assert evidence.latency_ms is None   # Never fabricated!
    assert evidence.checkout_successful is True

def test_recovery_verifier_active_checkout_probe_failure(db_session):
    """
    Test 4: Active Checkout Probe Failure.
    Endpoint is healthy, but real checkout transaction returns 500 error.
    -> Must return NOT_RECOVERED with observable probe error.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {
        "status": "healthy",
        "services": {
            "checkout-api": {"status": "Operational"}
        }
    }
    mock_adapter.probe_checkout.return_value = {
        "success": False,
        "status_code": 500,
        "latency_ms": 120.0,
        "order_id": None,
        "error": "HTTP 500: Database Connection Refused"
    }

    verifier = RecoveryVerifier(adapter=mock_adapter)
    evidence = verifier.verify(
        db=db_session,
        incident_id="inc_probe_fail",
        target_service="checkout-api",
        action="restart_service"
    )

    assert evidence.status == RecoveryStatus.NOT_RECOVERED
    assert evidence.healthy is False
    assert evidence.checkout_successful is False
    assert any("probe failed" in r.lower() for r in evidence.reasons)

def test_recovery_verifier_degraded_target(db_session):
    """
    Test 5: Target Service Degraded in Health Endpoint.
    -> Must return NOT_RECOVERED.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {
        "status": "degraded",
        "services": {
            "order-api": {"status": "Degraded"}
        }
    }
    mock_adapter.probe_checkout.return_value = {
        "success": False,
        "status_code": 504,
        "latency_ms": 3000.0,
        "order_id": None,
        "error": "HTTP 504: Gateway Timeout"
    }

    verifier = RecoveryVerifier(adapter=mock_adapter)
    evidence = verifier.verify(
        db=db_session,
        incident_id="inc_degraded_1",
        target_service="order-api",
        action="restart_service"
    )

    assert evidence.status == RecoveryStatus.NOT_RECOVERED
    assert evidence.healthy is False

def test_recovery_verifier_insufficient_evidence_unknown(db_session):
    """
    Test 6: Insufficient Evidence -> UNKNOWN.
    Adapter is unreachable (ShopFlow offline), no probe possible, no metrics.
    -> Must return UNKNOWN without assuming failure or success.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {"status": "unreachable"}
    mock_adapter.probe_checkout.return_value = {
        "success": False,
        "status_code": 0,
        "latency_ms": 0.0,
        "order_id": None,
        "error": "Connection refused to ShopFlow"
    }

    verifier = RecoveryVerifier(adapter=mock_adapter)
    evidence = verifier.verify(
        db=db_session,
        incident_id="inc_unknown_1",
        target_service="product-api",
        action="restart_service"
    )

    assert evidence.status == RecoveryStatus.UNKNOWN
    assert evidence.healthy is False
    assert evidence.checkout_successful is None
    assert any("UNKNOWN" in r for r in evidence.reasons)

def test_recovery_verifier_simulated_remediation_flow(db_session):
    """
    Test 7: Full flow with RemediationService in SIMULATION mode.
    Tests that simulation execution safely invokes RecoveryVerifier.
    """
    mock_adapter = MagicMock()
    mock_adapter.get_health.return_value = {
        "status": "healthy",
        "services": {
            "order-api": {"status": "Operational"}
        }
    }
    mock_adapter.probe_checkout.return_value = {
        "success": True,
        "status_code": 200,
        "latency_ms": 40.0,
        "order_id": "ord_sim_flow_1",
        "error": None
    }

    # Setup incident in DB
    incident_data = {
        "incident_id": "inc_sim_flow_1",
        "title": "Order API Simulated Fault",
        "severity": "CRITICAL",
        "status": "OPEN",
        "started_at": "2026-09-04T12:00:00Z",
        "alert_count": 1,
        "alert_ids": ["alt_sim_1"],
        "affected_services": ["order-api"],
        "correlation_score": 0.9
    }
    TelemetryRepository.save_incidents(db_session, [incident_data])
    TelemetryRepository.save_incident_diagnosis(db_session, "inc_sim_flow_1", {
        "root_cause_service": "order-api",
        "confidence_score": 0.88,
        "recommended_action": "Restart order-api instance"
    })

    verifier = RecoveryVerifier(adapter=mock_adapter)
    svc = RemediationService(recovery_verifier=verifier)

    req = RemediationRequest(
        action="restart_service",
        target_service="order-api",
        mode="SIMULATION"
    )
    result = svc.remediate_incident(db=db_session, incident_id="inc_sim_flow_1", request=req)

    assert result.decision.value == "APPROVED"
    assert result.execution_status.value == "SIMULATED_SUCCESS"
    assert result.recovery_status == RecoveryStatus.RECOVERED
    assert result.recovery_evidence is not None
    assert result.recovery_evidence.checkout_successful is True

