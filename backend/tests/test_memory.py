import pytest
from app.memory.hindsight_client import HindsightClient
from app.memory.service import MemoryService
from app.memory.models import HindsightMemoryItem, HindsightRecallResult
from app.root_cause.prompt_builder import build_diagnosis_prompt

def test_hindsight_client_retain_and_recall():
    client = HindsightClient(enabled=True)
    # Clear local demo bank for clean test
    client.clear_bank()

    # Retain test incident
    success = client.retain_incident(
        incident_id="inc_test_101",
        title="PostgreSQL Pool Exhaustion",
        content="Database connection pool exhausted under high traffic causing checkout errors.",
        affected_services=["postgresql", "order-api", "checkout-api"],
        root_cause_service="postgresql",
        remediation_action="reset_db_connection_pool",
        recovery_verified=True,
        tags=["test", "db"]
    )
    assert success is True

    # Recall memory
    recall_res = client.recall_memories(
        query="PostgreSQL query latency and pool saturation",
        affected_services=["postgresql", "checkout-api"],
        top_k=2
    )

    assert recall_res.enabled is True
    assert recall_res.memories_recalled >= 1
    assert recall_res.status in ("OK", "EMPTY")
    assert "HISTORICAL INCIDENT MEMORY" in recall_res.formatted_context
    assert "postgresql" in recall_res.formatted_context.lower()

def test_empty_memory_recall_does_not_break_prompt():
    client = HindsightClient(enabled=True)
    client.clear_bank()

    recall_res = client.recall_memories(
        query="Non-existent service failure xyz",
        affected_services=["unknown-svc"],
        top_k=2
    )

    incident_data = {
        "incident_id": "inc_999",
        "title": "Test Incident",
        "affected_services": ["unknown-svc"],
        "alert_count": 1
    }

    prompt = build_diagnosis_prompt(incident_data, hindsight_context=recall_res.formatted_context)
    assert "INCIDENT SUMMARY:" in prompt
    assert "unknown-svc" in prompt

def test_prompt_builder_injects_hindsight_context():
    incident_data = {
        "incident_id": "inc_202",
        "title": "Order API Latency Spike",
        "affected_services": ["order-api", "postgresql"],
        "alert_count": 5
    }

    mock_hindsight_context = (
        "=== HISTORICAL INCIDENT MEMORY (HINDSIGHT RECALL) ===\n"
        "Incident Title: PostgreSQL Pool Exhaustion\n"
        "Identified Root Cause: postgresql\n"
        "Successful Remediation: reset_db_connection_pool\n"
        "====================================================="
    )

    prompt = build_diagnosis_prompt(incident_data, hindsight_context=mock_hindsight_context)
    
    # Assert both historical memory and current telemetry exist in prompt
    assert "HISTORICAL INCIDENT MEMORY" in prompt
    assert "PostgreSQL Pool Exhaustion" in prompt
    assert "INCIDENT SUMMARY:" in prompt
    assert "inc_202" in prompt

def test_memory_service_graceful_exception_handling():
    service = MemoryService()
    # Test recall on empty/malformed incident dict
    res = service.recall_similar_incidents({})
    assert isinstance(res, HindsightRecallResult)
    assert res.memories_recalled == 0
