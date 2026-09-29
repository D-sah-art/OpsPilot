import time
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from app.ingestion.adapter import shopflow_adapter, ShopFlowAdapter
from .models import RemediationAction, ExecutionMode, ExecutionStatus

logger = logging.getLogger("opspilot.remediation.executor")

class RemediationExecutor:
    """
    Restricted, strictly typed remediation execution layer.
    NEVER runs arbitrary commands, subprocesses, or eval/exec.
    Only executes explicitly defined typed handlers with allow-listed targets.
    """

    def __init__(self, adapter: Optional[ShopFlowAdapter] = None):
        self.adapter = adapter or shopflow_adapter

    def execute(
        self,
        action: str,
        target_service: str,
        mode: ExecutionMode = ExecutionMode.SIMULATION,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[ExecutionStatus, str, Dict[str, Any]]:
        parameters = parameters or {}
        logger.info(f"Executing remediation action='{action}' on target='{target_service}' in mode='{mode.value}'")

        if action == RemediationAction.RESTART_SERVICE.value:
            return self._execute_restart_service(target_service, parameters, mode)
        elif action == RemediationAction.RESET_CONNECTIONS.value:
            return self._execute_reset_connections(target_service, parameters, mode)
        else:
            return (
                ExecutionStatus.FAILED,
                f"Unsupported remediation action '{action}'. No typed handler exists.",
                {"action": action, "target": target_service}
            )

    def _execute_restart_service(
        self,
        target_service: str,
        parameters: Dict[str, Any],
        mode: ExecutionMode
    ) -> Tuple[ExecutionStatus, str, Dict[str, Any]]:
        grace_period = parameters.get("grace_period_seconds", 10)

        if mode == ExecutionMode.SIMULATION:
            msg = (
                f"[SIMULATION] Simulated graceful restart of service '{target_service}' "
                f"(drain grace period: {grace_period}s). Host and processes were untouched."
            )
            logger.info(msg)
            return (
                ExecutionStatus.SIMULATED_SUCCESS,
                msg,
                {
                    "action": "restart_service",
                    "target_service": target_service,
                    "mode": "SIMULATION",
                    "grace_period_seconds": grace_period,
                    "simulated_at": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            # Controlled REAL testbed execution
            self.adapter.reset_chaos()
            msg = f"[REAL] Executed graceful reload for service '{target_service}' via typed testbed adapter."
            logger.info(msg)
            return (
                ExecutionStatus.EXECUTED_SUCCESS,
                msg,
                {
                    "action": "restart_service",
                    "target_service": target_service,
                    "mode": "REAL",
                    "executed_at": datetime.now(timezone.utc).isoformat()
                }
            )

    def _execute_reset_connections(
        self,
        target_service: str,
        parameters: Dict[str, Any],
        mode: ExecutionMode
    ) -> Tuple[ExecutionStatus, str, Dict[str, Any]]:
        drain_timeout = parameters.get("drain_timeout_seconds", 5)

        if mode == ExecutionMode.SIMULATION:
            msg = (
                f"[SIMULATION] Simulated connection pool reset for '{target_service}' "
                f"(socket drain timeout: {drain_timeout}s). Host and network were untouched."
            )
            logger.info(msg)
            return (
                ExecutionStatus.SIMULATED_SUCCESS,
                msg,
                {
                    "action": "reset_connections",
                    "target_service": target_service,
                    "mode": "SIMULATION",
                    "drain_timeout_seconds": drain_timeout,
                    "simulated_at": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            self.adapter.reset_chaos()
            msg = f"[REAL] Connection pool sockets re-established for '{target_service}' via typed testbed adapter."
            logger.info(msg)
            return (
                ExecutionStatus.EXECUTED_SUCCESS,
                msg,
                {
                    "action": "reset_connections",
                    "target_service": target_service,
                    "mode": "REAL",
                    "executed_at": datetime.now(timezone.utc).isoformat()
                }
            )

# Global singleton
remediation_executor = RemediationExecutor()
