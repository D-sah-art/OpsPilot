import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import uuid

from app.database.repository import TelemetryRepository
from .models import (
    RemediationRequest,
    RemediationResult,
    SafetyGateResult,
    SafetyDecision,
    ExecutionMode,
    ExecutionStatus,
    RecoveryStatus,
    RecoveryEvidence
)
from .safety_gate import RemediationSafetyGate, remediation_safety_gate
from .executor import RemediationExecutor, remediation_executor
from .recovery import RecoveryVerifier, recovery_verifier as default_recovery_verifier

logger = logging.getLogger("opspilot.remediation.service")

class RemediationService:
    """
    Orchestrates safety-gated remediation:
    Safety Gate -> Executor (Simulation / Real) -> Recovery Verification -> Immutable Audit Trail -> State Update.
    """

    def __init__(
        self,
        safety_gate: Optional[RemediationSafetyGate] = None,
        executor: Optional[RemediationExecutor] = None,
        recovery_verifier: Optional[RecoveryVerifier] = None
    ):
        self.safety_gate = safety_gate or remediation_safety_gate
        self.executor = executor or remediation_executor
        self.recovery_verifier = recovery_verifier or default_recovery_verifier

    def remediate_incident(
        self,
        db: Session,
        incident_id: str,
        request: Optional[RemediationRequest] = None
    ) -> RemediationResult:
        req = request or RemediationRequest()
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        now_ts = datetime.now(timezone.utc).isoformat()

        incident = TelemetryRepository.get_incident_by_id(db, incident_id=incident_id)
        if not incident:
            # Record failed audit for non-existent incident
            audit_data = {
                "audit_id": audit_id,
                "incident_id": incident_id,
                "timestamp": now_ts,
                "root_cause_service": None,
                "confidence": 0.0,
                "action": req.action or "unknown",
                "target_service": req.target_service or "unknown",
                "decision": SafetyDecision.REJECTED.value,
                "reason": f"Incident '{incident_id}' not found.",
                "execution_mode": req.mode or "SIMULATION",
                "execution_status": ExecutionStatus.FAILED.value,
                "recovery_status": RecoveryStatus.UNKNOWN.value,
                "actor": req.requested_by,
                "allowlist_policy": {},
                "details": {"error": "Incident not found"}
            }
            TelemetryRepository.save_audit_record(db, audit_data)
            return RemediationResult(
                audit_id=audit_id,
                incident_id=incident_id,
                action=req.action or "unknown",
                target_service=req.target_service or "unknown",
                decision=SafetyDecision.REJECTED,
                execution_mode=ExecutionMode.SIMULATION,
                execution_status=ExecutionStatus.FAILED,
                reason=f"Incident '{incident_id}' not found.",
                recovery_status=RecoveryStatus.UNKNOWN,
                timestamp=now_ts
            )

        diagnosis = incident.get("diagnosis") or {}
        root_cause_service = incident.get("root_cause_service") or diagnosis.get("root_cause_service")
        confidence = float(diagnosis.get("confidence_score", 0.0))

        # 1. Evaluate Safety Gate
        gate_res = self.safety_gate.evaluate(
            db=db,
            incident_id=incident_id,
            action=req.action,
            target_service=req.target_service,
            mode=req.mode,
            parameters=req.parameters,
            force=req.force
        )

        # 2. Handle Rejection or Human Review
        if not gate_res.allowed:
            logger.info(f"Remediation blocked by safety gate for '{incident_id}': {gate_res.reason}")
            audit_data = {
                "audit_id": audit_id,
                "incident_id": incident_id,
                "timestamp": now_ts,
                "root_cause_service": root_cause_service,
                "confidence": confidence,
                "action": gate_res.action,
                "target_service": gate_res.target_service,
                "decision": gate_res.decision.value,
                "reason": gate_res.reason,
                "execution_mode": gate_res.execution_mode.value,
                "execution_status": ExecutionStatus.SKIPPED.value,
                "recovery_status": RecoveryStatus.UNKNOWN.value,
                "actor": req.requested_by,
                "allowlist_policy": gate_res.allowlist_policy,
                "details": {
                    "conditions": [c.model_dump() for c in gate_res.conditions]
                }
            }
            TelemetryRepository.save_audit_record(db, audit_data)
            return RemediationResult(
                audit_id=audit_id,
                incident_id=incident_id,
                root_cause_service=root_cause_service,
                confidence=confidence,
                action=gate_res.action,
                target_service=gate_res.target_service,
                decision=gate_res.decision,
                execution_mode=gate_res.execution_mode,
                execution_status=ExecutionStatus.SKIPPED,
                reason=gate_res.reason,
                recovery_status=RecoveryStatus.UNKNOWN,
                safety_gate_result=gate_res,
                timestamp=now_ts
            )

        # 3. Execute Approved Action (Simulation or Real)
        exec_status, exec_reason, exec_details = self.executor.execute(
            action=gate_res.action,
            target_service=gate_res.target_service,
            mode=gate_res.execution_mode,
            parameters=req.parameters
        )

        # 4. Recovery Verification Layer
        recovery_evidence = self.recovery_verifier.verify(
            db=db,
            incident_id=incident_id,
            target_service=gate_res.target_service,
            action=gate_res.action
        )

        # 5. Update Incident Lifecycle State
        if recovery_evidence.status == RecoveryStatus.RECOVERED:
            TelemetryRepository.update_incident_status(
                db=db,
                incident_id=incident_id,
                status="MITIGATED",
                resolved_at=now_ts
            )
            logger.info(f"Incident '{incident_id}' marked as MITIGATED following recovery verification.")

        # 5b. Retain Completed Incident Resolution into Hindsight Vector Memory
        try:
            from app.memory.service import memory_service
            memory_service.retain_incident_resolution(
                incident_data=incident,
                root_cause_data={
                    "root_cause_service": root_cause_service,
                    "root_cause_summary": f"Incident in {root_cause_service} mitigated via {gate_res.action}",
                    "confidence_score": confidence
                },
                remediation_data={
                    "action": gate_res.action,
                    "status": gate_res.decision.value
                },
                recovery_data={
                    "is_recovered": recovery_evidence.status == RecoveryStatus.RECOVERED,
                    "details": {
                        "health_status": "HEALTHY" if recovery_evidence.healthy else "DEGRADED",
                        "active_alerts_count": 0 if recovery_evidence.status == RecoveryStatus.RECOVERED else 1
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Notice during Hindsight resolution retention: {e}")

        # 6. Record Immutable Audit Trail
        audit_data = {
            "audit_id": audit_id,
            "incident_id": incident_id,
            "timestamp": now_ts,
            "root_cause_service": root_cause_service,
            "confidence": confidence,
            "action": gate_res.action,
            "target_service": gate_res.target_service,
            "decision": gate_res.decision.value,
            "reason": exec_reason,
            "execution_mode": gate_res.execution_mode.value,
            "execution_status": exec_status.value,
            "recovery_status": recovery_evidence.status.value,
            "actor": req.requested_by,
            "allowlist_policy": gate_res.allowlist_policy,
            "details": {
                "execution_details": exec_details,
                "recovery_evidence": recovery_evidence.model_dump(),
                "conditions": [c.model_dump() for c in gate_res.conditions]
            }
        }
        TelemetryRepository.save_audit_record(db, audit_data)

        return RemediationResult(
            audit_id=audit_id,
            incident_id=incident_id,
            root_cause_service=root_cause_service,
            confidence=confidence,
            action=gate_res.action,
            target_service=gate_res.target_service,
            decision=gate_res.decision,
            execution_mode=gate_res.execution_mode,
            execution_status=exec_status,
            reason=exec_reason,
            recovery_status=recovery_evidence.status,
            recovery_evidence=recovery_evidence,
            safety_gate_result=gate_res,
            timestamp=now_ts
        )

    def verify_recovery(
        self,
        db: Session,
        incident_id: str
    ) -> RecoveryEvidence:
        incident = TelemetryRepository.get_incident_by_id(db, incident_id=incident_id)
        if not incident:
            return RecoveryEvidence(
                status=RecoveryStatus.UNKNOWN,
                healthy=False,
                signals_evaluated=[],
                reasons=[f"Incident '{incident_id}' not found."]
            )
        target = incident.get("root_cause_service") or "unknown"
        return self.recovery_verifier.verify(
            db=db,
            incident_id=incident_id,
            target_service=target,
            action="verify_status"
        )

    def get_latest_remediation(self, db: Session, incident_id: str) -> Optional[Dict[str, Any]]:
        return TelemetryRepository.get_latest_audit_for_incident(db, incident_id=incident_id)

    def get_audits(self, db: Session, incident_id: str) -> List[Dict[str, Any]]:
        return TelemetryRepository.get_audits_for_incident(db, incident_id=incident_id)

# Global singleton
remediation_service = RemediationService()
