from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

def default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class SystemEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=default_timestamp)
    service: str
    event_type: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
