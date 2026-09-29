from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

def current_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class ChaosStage(BaseModel):
    stage: int
    name: str
    offset_seconds: int
    service: str
    state: str  # Operational, Degraded, Major Outage, Recovering
    customer_impact: str = "none"
    description: str
    metrics_override: Dict[str, Any] = Field(default_factory=dict)

class ChaosScenario(BaseModel):
    id: str
    name: str
    description: str
    severity: str
    primary_fault_service: str
    duration_seconds: int = 60
    stages: List[ChaosStage] = Field(default_factory=list)

class ChaosStatus(BaseModel):
    active_scenario: Optional[str] = None
    scenario_name: Optional[str] = None
    state: str = "IDLE"  # IDLE, RUNNING, RECOVERING, COMPLETED
    started_at: Optional[str] = None
    elapsed_seconds: int = 0
    current_stage: int = 0
    total_stages: int = 0
    affected_services: List[str] = Field(default_factory=list)
    alert_count: int = 0
    event_count: int = 0
    log_count: int = 0
    recovery_status: str = "HEALTHY"
    demo_mode: bool = True
