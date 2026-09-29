from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class HindsightMemoryItem(BaseModel):
    id: str = Field(description="Unique identifier for the retained incident memory")
    incident_id: str = Field(description="Associated OpsPilot incident ID")
    title: str = Field(description="Short title or signature of the incident")
    content: str = Field(description="Full structured summary of the incident and resolution")
    affected_services: List[str] = Field(default_factory=list, description="Services affected during the incident")
    root_cause_service: Optional[str] = Field(default=None, description="Identified root cause microservice")
    remediation_action: Optional[str] = Field(default=None, description="Remediation action taken")
    recovery_verified: bool = Field(default=False, description="Whether recovery verification passed")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    timestamp: str = Field(description="ISO timestamp of memory retention")

class HindsightRecallResult(BaseModel):
    enabled: bool = Field(default=True, description="Whether Hindsight memory system is enabled")
    connection_status: str = Field(default="CONNECTED_TO_HINDSIGHT", description="Status: CONNECTED_TO_HINDSIGHT, HINDSIGHT_UNAVAILABLE, LOCAL_FALLBACK, DISABLED")
    memory_source: str = Field(default="Vectorize Hindsight Engine", description="Source: Vectorize Hindsight Engine, Local Fallback Cache, None")
    status: str = Field(default="OK", description="Status string: OK, DEGRADED, OFFLINE, EMPTY")
    bank_id: str = Field(default="opspilot-incidents-bank", description="Hindsight memory bank identifier")
    memories_recalled: int = Field(default=0, description="Count of relevant memories retrieved")
    memories: List[HindsightMemoryItem] = Field(default_factory=list, description="List of structured recalled memories")
    formatted_context: str = Field(default="", description="Sanitized text block ready for LLM prompt injection")

