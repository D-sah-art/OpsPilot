from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class Service(BaseModel):
    service_id: str
    name: str
    type: str
    status: str = "Operational"
    metadata: Dict[str, Any] = Field(default_factory=dict)
