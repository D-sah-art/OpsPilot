import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.database.repository import TelemetryRepository
from .models import SafetyDecision, ExecutionMode, SafetyGateResult, SafetyConditionCheck
from .allowlist import RemediationAllowlist, remediation_allowlist

logger = logging.getLogger("opspilot.remediation.safety_gate")

BANNED_COMMAND_PATTERNS = [
    r"\b(sudo|systemctl|service|docker|kubectl|helm|bash|sh|zsh|kill|pkill|rm\s+-rf|chmod|chown|eval|exec)\b",
    r"(\$\(.*\)|`.*`|\|.*bash|;\s*rm\s+)"
]

class RemediationSafetyGate:
    """
    Evaluates 10 deterministic safety conditions before any remediation execution.
    Guarantees that no unsafe, arbitrary, low-confidence, or unapproved actions can execute.
    """

    def __init__(self, allowlist: Optional[RemediationAllowlist] = None):
        self.allowlist = allowlist or remediation_allowlist

    def evaluate(
        self,
        db: Session,
        incident_id: str,
        action: Optional[str] = None,
        target_service: Optional[str] = None,
        mode: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> SafetyGateResult:
        parameters = parameters or {}
        conditions: List[SafetyConditionCheck] = []
        failed_reasons: List[str] = []

        # 1. Condition 1: Incident exists
        incident = TelemetryRepository.get_incident_by_id(db, incident_id=incident_id)
        if incident:
            conditions.append(SafetyConditionCheck(
                condition_number=1,
                name="Incident Existence",
                passed=True,
                detail=f"Incident '{incident_id}' exists in database."
            ))
        else:
            msg = f"Incident '{incident_id}' not found in database."
            conditions.append(SafetyConditionCheck(
                condition_number=1,
                name="Incident Existence",
                passed=False,
                detail=msg
            ))
            return self._build_rejection(
                decision=SafetyDecision.REJECTED,
                action=action or "unknown",
                target_service=target_service or "unknown",
                execution_mode=ExecutionMode.SIMULATION,
                reason=msg,
                conditions=conditions
            )

        # 2. Condition 2: Actionable status
        status = (incident.get("status") or "OPEN").upper()
        if status in ["OPEN", "INVESTIGATING"]:
            conditions.append(SafetyConditionCheck(
                condition_number=2,
                name="Actionable State",
                passed=True,
                detail=f"Incident status is '{status}'."
            ))
        else:
            msg = f"Incident status is '{status}', not in actionable state (OPEN or INVESTIGATING)."
            conditions.append(SafetyConditionCheck(
                condition_number=2,
                name="Actionable State",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 3. Condition 3: Root-cause diagnosis exists
        diagnosis = incident.get("diagnosis") or {}
        if diagnosis and diagnosis.get("root_cause_service"):
            conditions.append(SafetyConditionCheck(
                condition_number=3,
                name="Diagnosis Existence",
                passed=True,
                detail=f"Root-cause diagnosis exists for incident."
            ))
        else:
            msg = "No root-cause diagnosis found for incident. Run diagnosis before attempting remediation."
            conditions.append(SafetyConditionCheck(
                condition_number=3,
                name="Diagnosis Existence",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 4. Condition 4: Root-cause service is known
        root_cause_service = incident.get("root_cause_service") or diagnosis.get("root_cause_service")
        if root_cause_service and root_cause_service.lower() not in ["unknown", "none", ""]:
            conditions.append(SafetyConditionCheck(
                condition_number=4,
                name="Root Cause Service Known",
                passed=True,
                detail=f"Identified root cause service is '{root_cause_service}'."
            ))
        else:
            msg = "Root cause service is unknown or unspecified."
            conditions.append(SafetyConditionCheck(
                condition_number=4,
                name="Root Cause Service Known",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # Resolve target service & action if not explicitly supplied
        effective_target = target_service or root_cause_service or "unknown"
        effective_action = action or self.allowlist.find_eligible_action_for_service(effective_target) or "unknown"

        # 5. Condition 5: Confidence is sufficient
        confidence = float(diagnosis.get("confidence_score", 0.0))
        min_conf = self.allowlist.get_min_confidence(effective_action)
        if confidence >= min_conf:
            conditions.append(SafetyConditionCheck(
                condition_number=5,
                name="Confidence Threshold",
                passed=True,
                detail=f"Evidence-derived confidence {confidence:.3f} meets policy threshold {min_conf:.2f}."
            ))
        else:
            msg = f"Evidence-derived confidence {confidence:.3f} is below policy minimum {min_conf:.2f} for '{effective_action}'."
            conditions.append(SafetyConditionCheck(
                condition_number=5,
                name="Confidence Threshold",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 6. Condition 6: Action exists in allow-list
        action_policy = self.allowlist.get_action_policy(effective_action)
        if action_policy is not None:
            conditions.append(SafetyConditionCheck(
                condition_number=6,
                name="Action Allow-List",
                passed=True,
                detail=f"Action '{effective_action}' is registered in the allow-list policy."
            ))
        else:
            msg = f"Action '{effective_action}' is not in the explicit allow-list."
            conditions.append(SafetyConditionCheck(
                condition_number=6,
                name="Action Allow-List",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 7. Condition 7: Target service allowed for action
        if self.allowlist.is_service_allowed(effective_action, effective_target):
            conditions.append(SafetyConditionCheck(
                condition_number=7,
                name="Target Service Allow-List",
                passed=True,
                detail=f"Target service '{effective_target}' is permitted for action '{effective_action}'."
            ))
        else:
            msg = f"Target service '{effective_target}' is not permitted for action '{effective_action}' in allow-list."
            conditions.append(SafetyConditionCheck(
                condition_number=7,
                name="Target Service Allow-List",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 8. Condition 8: Remediation enabled globally & for action
        global_en = self.allowlist.is_global_enabled()
        act_en = self.allowlist.is_action_enabled(effective_action)
        if global_en and act_en:
            conditions.append(SafetyConditionCheck(
                condition_number=8,
                name="Remediation Enabled",
                passed=True,
                detail="Remediation is enabled globally and for this action."
            ))
        else:
            msg = f"Remediation is disabled (global_enabled={global_en}, action_enabled={act_en})."
            conditions.append(SafetyConditionCheck(
                condition_number=8,
                name="Remediation Enabled",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 9. Condition 9: No duplicate execution
        recent_audits = TelemetryRepository.get_audits_for_incident(db, incident_id=incident_id, limit=5)
        has_completed_remediation = any(
            a.get("action") == effective_action and
            a.get("target_service") == effective_target and
            a.get("decision") == "APPROVED" and
            a.get("execution_status") in ["SIMULATED_SUCCESS", "EXECUTED_SUCCESS"]
            for a in recent_audits
        )
        if not has_completed_remediation or force:
            conditions.append(SafetyConditionCheck(
                condition_number=9,
                name="No Duplicate Remediation",
                passed=True,
                detail="No prior active/completed remediation for this action/target (or force=True)."
            ))
        else:
            msg = f"Action '{effective_action}' on '{effective_target}' was already successfully executed for this incident. Use force=True to re-run."
            conditions.append(SafetyConditionCheck(
                condition_number=9,
                name="No Duplicate Remediation",
                passed=False,
                detail=msg
            ))
            failed_reasons.append(msg)

        # 10. Condition 10: Security and typed parameter validation
        security_ok, sec_msg = self._validate_security_and_params(effective_action, parameters)
        if security_ok:
            conditions.append(SafetyConditionCheck(
                condition_number=10,
                name="Security & Parameter Safety",
                passed=True,
                detail="Request strictly conforms to typed allow-list schema and contains zero banned commands."
            ))
        else:
            conditions.append(SafetyConditionCheck(
                condition_number=10,
                name="Security & Parameter Safety",
                passed=False,
                detail=sec_msg
            ))
            failed_reasons.append(sec_msg)

        # Determine execution mode (Simulation is default)
        execution_mode = ExecutionMode.SIMULATION
        if mode and mode.upper() == "REAL":
            execution_mode = ExecutionMode.REAL

        # Final Safety Decision
        if not failed_reasons:
            return SafetyGateResult(
                decision=SafetyDecision.APPROVED,
                allowed=True,
                action=effective_action,
                target_service=effective_target,
                execution_mode=execution_mode,
                reason=f"All 10 safety conditions passed. Approved for {execution_mode.value} execution.",
                conditions=conditions,
                allowlist_policy=action_policy or {}
            )
        else:
            reasons_summary = "; ".join(failed_reasons)
            decision = SafetyDecision.HUMAN_REVIEW
            # If basic parameter injection or unlisted action, classify as REJECTED or HUMAN_REVIEW
            reason_msg = f"No safe automated fix available — flagged for human review. Reasons: {reasons_summary}"
            logger.warning(f"Incident '{incident_id}' remediation safety gate failed: {reason_msg}")
            return SafetyGateResult(
                decision=decision,
                allowed=False,
                action=effective_action,
                target_service=effective_target,
                execution_mode=execution_mode,
                reason=reason_msg,
                conditions=conditions,
                allowlist_policy=action_policy or {}
            )

    def _validate_security_and_params(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        # Check parameter values for dangerous command substrings
        for k, v in parameters.items():
            val_str = str(v)
            for pat in BANNED_COMMAND_PATTERNS:
                if re.search(pat, val_str, re.IGNORECASE) or re.search(pat, str(k), re.IGNORECASE):
                    return False, f"Security violation: banned command pattern detected in parameter '{k}'"

        # Validate against schema
        if action in ["restart_service", "reset_connections"]:
            return self.allowlist.validate_parameters(action, parameters)

        return True, "Valid"

    def _build_rejection(
        self,
        decision: SafetyDecision,
        action: str,
        target_service: str,
        execution_mode: ExecutionMode,
        reason: str,
        conditions: List[SafetyConditionCheck]
    ) -> SafetyGateResult:
        return SafetyGateResult(
            decision=decision,
            allowed=False,
            action=action,
            target_service=target_service,
            execution_mode=execution_mode,
            reason=reason,
            conditions=conditions,
            allowlist_policy={}
        )

# Global singleton
remediation_safety_gate = RemediationSafetyGate()
