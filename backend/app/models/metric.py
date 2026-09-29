from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

def default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class Metric(BaseModel):
    timestamp: str = Field(default_factory=default_timestamp)
    service: str
    metric_name: str
    value: float
    unit: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
