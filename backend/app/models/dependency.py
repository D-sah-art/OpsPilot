from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class Dependency(BaseModel):
    source: str
    target: str
    relationship: str = "calls"
    metadata: Dict[str, Any] = Field(default_factory=dict)
