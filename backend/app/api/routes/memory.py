from fastapi import APIRouter, Query
from typing import Dict, Any, List

from app.memory.service import memory_service, recall_similar_incidents
from app.memory.models import HindsightRecallResult

router = APIRouter(prefix="/api/memory", tags=["Hindsight Memory"])

@router.get("/status", summary="Get Hindsight memory system status")
def get_memory_status() -> Dict[str, Any]:
    from app.memory.hindsight_client import hindsight_client
    conn = hindsight_client.check_connection()
    return {
        "enabled": hindsight_client.enabled,
        "connection_status": conn.get("status", "HINDSIGHT_UNAVAILABLE"),
        "base_url": hindsight_client.base_url,
        "bank_id": hindsight_client.bank_id,
        "sdk_available": hindsight_client._sdk_client is not None,
        "details": conn
    }


@router.post("/clear", summary="Clear Hindsight demo memory bank for fresh demo runs")
def clear_memory_bank() -> Dict[str, str]:
    success = memory_service.clear_bank()
    if success:
        return {"status": "success", "message": "Hindsight memory bank cleared successfully."}
    return {"status": "error", "message": "Failed to clear Hindsight memory bank."}
