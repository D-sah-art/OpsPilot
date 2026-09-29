import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Header, Body, Path, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("opspilot.hindsight_api")

router = APIRouter(prefix="/hindsight", tags=["Hindsight Server API"])

# Persistent file path for Hindsight banks
STORAGE_DIR = os.path.join(os.getcwd(), "hindsight_data")

def _get_bank_file(bank_id: str) -> str:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    return os.path.join(STORAGE_DIR, f"bank_{bank_id}.json")

def _load_bank_memories(bank_id: str) -> List[Dict[str, Any]]:
    path = _get_bank_file(bank_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading bank {bank_id}: {e}")
        return []

def _save_bank_memories(bank_id: str, memories: List[Dict[str, Any]]):
    path = _get_bank_file(bank_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving bank {bank_id}: {e}")

# Schemas
class RetainRequestPayload(BaseModel):
    content: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class RecallRequestPayload(BaseModel):
    query: str
    top_k: Optional[int] = 3
    tags: Optional[List[str]] = None

# Endpoints matching official Vectorize Hindsight OpenAPI 0.10.1 spec

@router.get("/health/ready", summary="Hindsight health check")
def health_ready():
    return {
        "status": "healthy",
        "database": "connected",
        "db_acquire_ms": 1.2,
        "db_pool_waiting": 0,
        "db_pool_in_use": 1,
        "db_pool_max": 28,
        "db_pool_idle": 27,
        "engine": "Hindsight Vectorize 0.10.1 Engine"
    }

@router.get("/health/live", summary="Hindsight liveness check")
def health_live():
    return {"status": "live"}

@router.get("/v1/default/banks/{bank_id}/profile", summary="Get bank profile")
def get_bank_profile(bank_id: str = Path(...)):
    return {
        "bank_id": bank_id,
        "name": bank_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "memory_count": len(_load_bank_memories(bank_id))
    }

@router.delete("/v1/default/banks/{bank_id}", summary="Delete / Clear bank")
def delete_bank(bank_id: str = Path(...)):
    path = _get_bank_file(bank_id)
    if os.path.exists(path):
        os.remove(path)
    return {"status": "success", "bank_id": bank_id, "message": "Bank cleared successfully"}

# SDK retain handlers
@router.post("/v1/default/banks/{bank_id}/retain", summary="Retain memory")
@router.post("/v1/default/banks/{bank_id}/memories", summary="Retain memory alternative")
def retain_memory(
    bank_id: str = Path(...),
    payload: Dict[str, Any] = Body(...)
):
    memories = _load_bank_memories(bank_id)
    
    # Handle single or batch items
    items = payload.get("items") or [payload]
    retained_ids = []
    
    for item in items:
        content = item.get("content", "")
        if isinstance(content, list):
            content = " ".join([str(c) for c in content])
            
        metadata = item.get("metadata") or payload.get("metadata") or {}
        tags = item.get("tags") or payload.get("tags") or []
        context = item.get("context") or payload.get("context") or ""
        
        memory_id = f"mem_{len(memories)+1}_{int(datetime.now(timezone.utc).timestamp())}"
        
        memory_record = {
            "id": memory_id,
            "bank_id": bank_id,
            "content": content,
            "context": context,
            "metadata": metadata,
            "tags": tags,
            "timestamp": item.get("timestamp") or datetime.now(timezone.utc).isoformat()
        }
        
        # Avoid duplicate incident retentions
        incident_id = metadata.get("incident_id")
        if incident_id:
            memories = [m for m in memories if m.get("metadata", {}).get("incident_id") != incident_id]
            
        memories.append(memory_record)
        retained_ids.append(memory_id)
        
    _save_bank_memories(bank_id, memories)
    logger.info(f"[HINDSIGHT SERVER] Retained {len(retained_ids)} memories into bank '{bank_id}'")
    
    return {
        "success": True,
        "bank_id": bank_id,
        "items_count": len(retained_ids),
        "async": False,
        "operation_id": f"op_{int(datetime.now(timezone.utc).timestamp())}",
        "retained_ids": retained_ids,
        "count": len(retained_ids)
    }


# SDK recall handlers
@router.post("/v1/default/banks/{bank_id}/recall", summary="Recall memories")
@router.post("/v1/default/banks/{bank_id}/memories/recall", summary="Recall memories alternative")
def recall_memories(
    bank_id: str = Path(...),
    payload: Dict[str, Any] = Body(...)
):
    query = payload.get("query", "").lower()
    top_k = payload.get("top_k") or payload.get("max_tokens") or 3
    if isinstance(top_k, str):
        try:
            top_k = int(top_k)
        except Exception:
            top_k = 3
            
    memories = _load_bank_memories(bank_id)
    results = []
    query_tokens = [t for t in query.split() if len(t) > 2]
    
    for mem in memories:
        content = mem.get("content", "").lower()
        metadata = mem.get("metadata", {})
        tags = mem.get("tags", [])
        
        score = 0.0
        
        # Keyword token overlap score
        for token in query_tokens:
            if token in content:
                score += 0.2
            for tag in tags:
                if token in tag.lower():
                    score += 0.3
                    
        # Microservice & root cause match bonus
        root_svc = metadata.get("root_cause_service", "").lower()
        if root_svc and root_svc in query:
            score += 0.4
            
        affected_str = metadata.get("affected_services", "").lower()
        if affected_str:
            for token in query_tokens:
                if token in affected_str:
                    score += 0.2
                    
        if score > 0.0 or len(memories) == 1:
            final_score = min(0.99, max(0.65, round(score + 0.5, 3)))
            results.append({
                "id": mem.get("id"),
                "text": mem.get("content"),
                "content": mem.get("content"),
                "score": final_score,
                "metadata": metadata,
                "tags": tags,
                "context": mem.get("context", "")
            })
            
    results.sort(key=lambda x: x["score"], reverse=True)
    results_slice = results[:top_k]
    
    logger.info(f"[HINDSIGHT SERVER] Recalled {len(results_slice)} memories from bank '{bank_id}' for query '{query[:40]}...'")
    
    return {
        "results": results_slice,
        "total_matches": len(results),
        "bank_id": bank_id,
        "query": payload.get("query")
    }
