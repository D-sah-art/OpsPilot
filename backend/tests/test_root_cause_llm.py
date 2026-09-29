import json
import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.root_cause.llm_client import LLMClient
from app.root_cause.analyzer import RootCauseAnalyzer
from app.root_cause.fallback import DeterministicFallbackAnalyzer
from app.topology.graph import dependency_graph

@pytest.fixture
def sample_incident_data():
    return {
        "incident_id": "inc_llm_test_1",
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
                {"service": "order-api", "alert_type": "DB_QUERY_TIMEOUT", "timestamp": "2026-09-04T12:00:05Z"}
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

def test_llm_client_success_parsing(sample_incident_data):
    llm = LLMClient(api_key="sk-test-key", model="gpt-4o-mini")

    mock_response_content = json.dumps({
        "root_cause_service": "postgresql",
        "root_cause_summary": "Database table lock contention on orders table led to thread pool starvation.",
        "causal_narrative": "PostgreSQL suffered prolonged lock waits -> Order API timed out -> Checkout API returned 504 -> API Gateway opened circuit breaker.",
        "propagation_path": ["postgresql", "order-api", "checkout-api", "api-gateway"],
        "evidence_summary": [
            "Earliest alert at 12:00:00Z on postgresql for db_lock_wait_seconds=4.8s",
            "Cascaded along call chain to order-api and checkout-api",
            "High correlation score of 1.0 confirms unified single incident"
        ],
        "recommended_action": "Investigate long-running transactions and active locks on PostgreSQL. Check orders table query plans.",
        "confidence_score": 0.95
    })

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": mock_response_content}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = llm.diagnose_incident(sample_incident_data)

    assert res is not None
    assert res["root_cause_service"] == "postgresql"
    assert res["confidence_score"] == 0.95
    assert len(res["propagation_path"]) == 4

def test_llm_client_handles_markdown_code_fences(sample_incident_data):
    llm = LLMClient(api_key="sk-test-key", model="gpt-4o-mini")

    raw_markdown = (
        "```json\n"
        "{\n"
        '  "root_cause_service": "postgresql",\n'
        '  "root_cause_summary": "DB lock contention",\n'
        '  "causal_narrative": "DB locked -> timeouts",\n'
        '  "propagation_path": ["postgresql", "order-api"],\n'
        '  "evidence_summary": ["Lock contention alert first"],\n'
        '  "recommended_action": "Inspect active query locks on database.",\n'
        '  "confidence_score": 0.92\n'
        "}\n"
        "```"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": raw_markdown}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = llm.diagnose_incident(sample_incident_data)

    assert res is not None
    assert res["root_cause_service"] == "postgresql"

def test_llm_grounding_rejects_hallucinated_service(sample_incident_data):
    """
    Validates Requirement 2: Strict grounding.
    If LLM returns a hallucinated service (e.g. 'kubernetes-worker-node') not in affected_services,
    it must be rejected and return None so fallback takes over.
    """
    llm = LLMClient(api_key="sk-test-key", model="gpt-4o-mini")

    hallucinated_resp = json.dumps({
        "root_cause_service": "kubernetes-worker-node-42",
        "root_cause_summary": "OOM killer invoked on cluster node",
        "causal_narrative": "Worker node went down",
        "propagation_path": ["kubernetes-worker-node-42"],
        "evidence_summary": ["Node went dark"],
        "recommended_action": "Check node status",
        "confidence_score": 0.99
    })

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": hallucinated_resp}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = llm.diagnose_incident(sample_incident_data)

    assert res is None  # Grounding rejection

def test_llm_safety_rejects_executable_commands(sample_incident_data):
    """
    Validates safety filter: recommended_action must NOT contain executable shell commands.
    """
    llm = LLMClient(api_key="sk-test-key", model="gpt-4o-mini")

    dangerous_resp = json.dumps({
        "root_cause_service": "postgresql",
        "root_cause_summary": "DB lock contention",
        "causal_narrative": "DB locked",
        "propagation_path": ["postgresql"],
        "evidence_summary": ["Lock contention"],
        "recommended_action": "Run `sudo systemctl restart postgresql` and `docker kill shopflow-db` to fix it.",
        "confidence_score": 0.95
    })

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": dangerous_resp}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = llm.diagnose_incident(sample_incident_data)

    assert res is None  # Safety command rejection

def test_analyzer_falls_back_on_timeout(sample_incident_data):
    llm = LLMClient(api_key="sk-test-key", model="gpt-4o-mini")
    fallback = DeterministicFallbackAnalyzer(graph=dependency_graph)
    analyzer = RootCauseAnalyzer(llm_client=llm, fallback_analyzer=fallback, graph=dependency_graph)

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        res = analyzer.analyze("inc_llm_test_1", sample_incident_data)

    assert res.analysis_mode == "deterministic_fallback"
    assert res.root_cause_service == "postgresql"
    assert 0.0 <= res.confidence_score <= 1.0

def test_analyzer_uses_llm_when_valid(sample_incident_data):
    llm = LLMClient(api_key="sk-test-key", model="gpt-4o-mini")
    fallback = DeterministicFallbackAnalyzer(graph=dependency_graph)
    analyzer = RootCauseAnalyzer(llm_client=llm, fallback_analyzer=fallback, graph=dependency_graph)

    valid_llm_output = json.dumps({
        "root_cause_service": "postgresql",
        "root_cause_summary": "Exhausted connection pool and row-level lock contention on PostgreSQL.",
        "causal_narrative": "PostgreSQL lock contention caused cascading timeouts upstream.",
        "propagation_path": ["postgresql", "order-api", "checkout-api", "api-gateway"],
        "evidence_summary": ["Initial DB lock contention alert"],
        "recommended_action": "Review long transactions and slow queries on orders table.",
        "confidence_score": 0.94
    })

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": valid_llm_output}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = analyzer.analyze("inc_llm_test_1", sample_incident_data)

    assert res.analysis_mode == "llm"
    assert res.model_used == "gpt-4o-mini"
    assert res.root_cause_service == "postgresql"
    assert res.confidence_score == 0.94
    assert 0.0 <= res.confidence_breakdown.topological_clarity <= 1.0
