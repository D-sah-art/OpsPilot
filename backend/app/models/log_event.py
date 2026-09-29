from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

def default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class LogEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=default_timestamp)
    service: str
    level: str = "INFO"  # INFO, WARN, ERROR, DEBUG
    event: str
    message: str
    request_id: Optional[str] = None
    dependency: Optional[str] = None
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
