from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

def default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def default_audit_id() -> str:
    return f"aud_{uuid.uuid4().hex[:12]}"

class RemediationAction(str, Enum):
    RESTART_SERVICE = "restart_service"
    RESET_CONNECTIONS = "reset_connections"

class SafetyDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"

class ExecutionMode(str, Enum):
    SIMULATION = "SIMULATION"
    REAL = "REAL"

class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    SIMULATED_SUCCESS = "SIMULATED_SUCCESS"
    EXECUTED_SUCCESS = "EXECUTED_SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class RecoveryStatus(str, Enum):
    RECOVERED = "RECOVERED"
    NOT_RECOVERED = "NOT_RECOVERED"
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"

class SafetyConditionCheck(BaseModel):
    condition_number: int
    name: str
    passed: bool
    detail: str

class SafetyGateResult(BaseModel):
    decision: SafetyDecision
    allowed: bool
    action: str
    target_service: str
    execution_mode: ExecutionMode
    reason: str
    conditions: List[SafetyConditionCheck] = Field(default_factory=list)
    allowlist_policy: Dict[str, Any] = Field(default_factory=dict)

class RecoveryEvidence(BaseModel):
    status: RecoveryStatus
    healthy: bool
    active_alerts_count: int = 0
    error_rate: Optional[float] = None
    latency_ms: Optional[float] = None
    checkout_successful: Optional[bool] = None
    probe_latency_ms: Optional[float] = None
    signals_evaluated: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)

class RemediationRequest(BaseModel):
    action: Optional[str] = Field(None, description="Action to perform ('restart_service', 'reset_connections'). If omitted, inferred.")
    target_service: Optional[str] = Field(None, description="Target service. If omitted, inferred from incident root_cause_service.")
    mode: Optional[str] = Field(None, description="'SIMULATION' (default) or 'REAL'")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Typed parameters conforming to action policy")
    force: bool = Field(False, description="Force re-execution even if previously remediated")
    requested_by: str = Field("operator", description="Actor or identity requesting remediation")

class RemediationResult(BaseModel):
    audit_id: str = Field(default_factory=default_audit_id)
    incident_id: str
    root_cause_service: Optional[str] = None
    confidence: float = 0.0
    action: str
    target_service: str
    decision: SafetyDecision
    execution_mode: ExecutionMode
    execution_status: ExecutionStatus
    reason: str
    recovery_status: RecoveryStatus = RecoveryStatus.UNKNOWN
    recovery_evidence: Optional[RecoveryEvidence] = None
    safety_gate_result: Optional[SafetyGateResult] = None
    timestamp: str = Field(default_factory=default_timestamp)
