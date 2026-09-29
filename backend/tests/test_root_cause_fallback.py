import pytest
from app.root_cause.fallback import DeterministicFallbackAnalyzer
from app.root_cause.models import RootCauseAnalysis, ConfidenceBreakdown
from app.topology.graph import dependency_graph

def test_fallback_diagnoses_postgresql_for_cascade():
    analyzer = DeterministicFallbackAnalyzer(graph=dependency_graph)

    mock_incident_data = {
        "incident_id": "inc_test_cascade_1",
        "title": "Cascading Database Lock Contention",
        "severity": "CRITICAL",
        "alert_count": 29,
        "affected_services": ["api-gateway", "checkout-api", "order-api", "postgresql"],
        "correlation_score": 1.0,
        "correlation_evidence": {
            "temporal_span_seconds": 25.4,
            "earliest_alert": {
                "service": "postgresql",
                "alert_type": "DB_LOCK_CONTENTION",
                "metric": "db_lock_wait_seconds",
                "metric_value": 4.8,
                "timestamp": "2026-09-04T12:00:00Z"
            },
            "causal_chain": [
                {"service": "postgresql", "alert_type": "DB_LOCK_CONTENTION", "timestamp": "2026-09-04T12:00:00Z"},
                {"service": "order-api", "alert_type": "DB_QUERY_TIMEOUT", "timestamp": "2026-09-04T12:00:05Z"},
                {"service": "checkout-api", "alert_type": "HTTP_504_GATEWAY_TIMEOUT", "timestamp": "2026-09-04T12:00:10Z"},
                {"service": "api-gateway", "alert_type": "CIRCUIT_BREAKER_OPEN", "timestamp": "2026-09-04T12:00:15Z"}
            ],
            "dependency_paths": [
                ["api-gateway", "checkout-api", "order-api", "postgresql"]
            ],
            "top_pairwise_correlations": [
                {
                    "service_a": "order-api",
                    "service_b": "postgresql",
                    "total_score": 0.95
                }
            ]
        }
    }

    result = analyzer.analyze(
        incident_id="inc_test_cascade_1",
        incident_data=mock_incident_data
    )

    assert isinstance(result, RootCauseAnalysis)
    assert result.root_cause_service == "postgresql"
    assert result.analysis_mode == "deterministic_fallback"
    assert 0.0 <= result.confidence_score <= 1.0
    
    # Verify Confidence Breakdown
    breakdown = result.confidence_breakdown
    assert isinstance(breakdown, ConfidenceBreakdown)
    assert 0.0 <= breakdown.topological_clarity <= 1.0
    assert 0.0 <= breakdown.causal_consistency <= 1.0
    assert 0.0 <= breakdown.evidence_completeness <= 1.0
    assert 0.0 <= breakdown.symptom_breadth <= 1.0
    assert 0.0 <= breakdown.correlation_cohesion <= 1.0
    assert breakdown.causal_consistency >= 0.85  # Earliest alert was postgresql

    # Verify propagation path
    assert "postgresql" in result.propagation_path
    assert "api-gateway" in result.propagation_path

    # Verify no executable shell commands in recommendation
    assert "sudo" not in result.recommended_action
    assert "systemctl" not in result.recommended_action
    assert "docker" not in result.recommended_action
    assert "kill" not in result.recommended_action

def test_fallback_evidence_derived_confidence_difference():
    """
    Validates Requirement 1: Confidence is evidence-derived, not hardcoded.
    A well-connected cascade with early causal signals should score significantly higher
    confidence than an ambiguous, sparse, single-alert incident.
    """
    analyzer = DeterministicFallbackAnalyzer(graph=dependency_graph)

    # Strong connected cascade
    strong_incident = {
        "incident_id": "inc_strong",
        "affected_services": ["api-gateway", "checkout-api", "order-api", "postgresql"],
        "correlation_score": 1.0,
        "correlation_evidence": {
            "temporal_span_seconds": 12.0,
            "earliest_alert": {"service": "postgresql", "timestamp": "2026-09-04T12:00:00Z"},
            "causal_chain": [
                {"service": "postgresql", "timestamp": "2026-09-04T12:00:00Z"},
                {"service": "order-api", "timestamp": "2026-09-04T12:00:02Z"}
            ],
            "dependency_paths": [["api-gateway", "checkout-api", "order-api", "postgresql"]],
            "top_pairwise_correlations": [{"service_a": "order-api", "service_b": "postgresql", "total_score": 0.9}]
        }
    }

    # Weak/ambiguous incident: no causal chain, no dependency paths, single service
    weak_incident = {
        "incident_id": "inc_weak",
        "affected_services": ["inventory-api"],
        "correlation_score": 0.3,
        "correlation_evidence": {}
    }

    res_strong = analyzer.analyze("inc_strong", strong_incident)
    res_weak = analyzer.analyze("inc_weak", weak_incident)

    assert 0.0 <= res_strong.confidence_score <= 1.0
    assert 0.0 <= res_weak.confidence_score <= 1.0
    assert res_strong.confidence_score > res_weak.confidence_score
    assert res_strong.confidence_breakdown.evidence_completeness > res_weak.confidence_breakdown.evidence_completeness

def test_fallback_single_service_incident():
    analyzer = DeterministicFallbackAnalyzer(graph=dependency_graph)
    single_incident = {
        "incident_id": "inc_single",
        "affected_services": ["auth-service"],
        "correlation_score": 1.0,
        "correlation_evidence": {
            "earliest_alert": {"service": "auth-service", "alert_type": "HIGH_AUTH_LATENCY"},
            "causal_chain": [{"service": "auth-service", "alert_type": "HIGH_AUTH_LATENCY"}]
        }
    }
    res = analyzer.analyze("inc_single", single_incident)
    assert res.root_cause_service == "auth-service"
    assert res.propagation_path == ["auth-service"]
    assert 0.0 <= res.confidence_score <= 1.0
