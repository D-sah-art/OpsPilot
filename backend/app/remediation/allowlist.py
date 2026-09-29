import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.config import settings

logger = logging.getLogger("opspilot.remediation.allowlist")

DEFAULT_FALLBACK_ALLOWLIST = {
    "version": "1.0",
    "global_enabled": True,
    "simulation_default": True,
    "actions": {
        "restart_service": {
            "enabled": True,
            "simulation_default": True,
            "min_confidence": 0.70,
            "description": "Gracefully restart stateless application service instances",
            "allowed_services": ["order-api", "checkout-api", "product-api", "auth-service"],
            "parameters_schema": {
                "grace_period_seconds": {"type": "integer", "default": 10, "min": 1, "max": 60}
            }
        },
        "reset_connections": {
            "enabled": True,
            "simulation_default": True,
            "min_confidence": 0.75,
            "description": "Drain and re-establish connection pool sockets to downstream dependencies",
            "allowed_services": ["order-api", "checkout-api", "postgresql"],
            "parameters_schema": {
                "drain_timeout_seconds": {"type": "integer", "default": 5, "min": 1, "max": 30}
            }
        }
    }
}

class RemediationAllowlist:
    """
    Manages the deterministic YAML remediation allow-list policy.
    Ensures that only explicitly approved actions and services are eligible for remediation.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or settings.remediation_allowlist_path
        self.policy: Dict[str, Any] = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        # Search multiple prospective locations for the YAML file
        candidates = [
            Path(self.config_path),
            Path.cwd() / self.config_path,
            Path.cwd() / "config" / "remediation_allowlist.yaml",
            Path(__file__).resolve().parent.parent.parent / "config" / "remediation_allowlist.yaml",
            Path(__file__).resolve().parent.parent.parent.parent / "config" / "remediation_allowlist.yaml",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict) and "actions" in data:
                        logger.info(f"Loaded remediation allow-list policy from {candidate}")
                        return data
                except Exception as e:
                    logger.warning(f"Failed to read allow-list at {candidate}: {e}")

        logger.warning("No valid remediation allow-list file found; using default built-in policy")
        return DEFAULT_FALLBACK_ALLOWLIST

    def reload(self):
        self.policy = self._load_policy()

    def is_global_enabled(self) -> bool:
        return bool(self.policy.get("global_enabled", True) and settings.remediation_enabled)

    def is_simulation_default(self) -> bool:
        return bool(self.policy.get("simulation_default", True))

    def get_action_policy(self, action_name: str) -> Optional[Dict[str, Any]]:
        actions = self.policy.get("actions", {})
        return actions.get(action_name)

    def is_action_enabled(self, action_name: str) -> bool:
        act = self.get_action_policy(action_name)
        return bool(act and act.get("enabled", False))

    def is_service_allowed(self, action_name: str, service_name: str) -> bool:
        act = self.get_action_policy(action_name)
        if not act or not act.get("enabled", False):
            return False
        allowed_list = act.get("allowed_services", [])
        return service_name in allowed_list

    def get_min_confidence(self, action_name: str) -> float:
        act = self.get_action_policy(action_name)
        if act and "min_confidence" in act:
            return float(act["min_confidence"])
        return 0.70

    def validate_parameters(self, action_name: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates typed parameters against schema in allow-list policy.
        Rejects arbitrary or unlisted parameters.
        """
        act = self.get_action_policy(action_name)
        if not act:
            return False, f"Action '{action_name}' does not exist in allow-list"

        schema = act.get("parameters_schema", {})
        for param_key, param_val in parameters.items():
            if param_key not in schema:
                return False, f"Unrecognized parameter '{param_key}' for action '{action_name}'"
            param_spec = schema[param_key]
            expected_type = param_spec.get("type")
            if expected_type == "integer" and not isinstance(param_val, int):
                return False, f"Parameter '{param_key}' must be an integer, got {type(param_val).__name__}"
            if "min" in param_spec and param_val < param_spec["min"]:
                return False, f"Parameter '{param_key}' value {param_val} is below minimum {param_spec['min']}"
            if "max" in param_spec and param_val > param_spec["max"]:
                return False, f"Parameter '{param_key}' value {param_val} exceeds maximum {param_spec['max']}"

        return True, "Parameters valid"

    def find_eligible_action_for_service(self, service_name: str) -> Optional[str]:
        """
        Finds the first enabled allow-listed action for a given service.
        """
        actions = self.policy.get("actions", {})
        for act_name, act_conf in actions.items():
            if act_conf.get("enabled") and service_name in act_conf.get("allowed_services", []):
                return act_name
        return None

    def get_all_policies(self) -> Dict[str, Any]:
        return self.policy

# Global singleton
remediation_allowlist = RemediationAllowlist()
