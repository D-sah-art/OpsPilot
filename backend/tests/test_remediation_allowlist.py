import pytest
from app.remediation.allowlist import RemediationAllowlist

def test_allowlist_loading_and_defaults():
    allowlist = RemediationAllowlist()
    assert allowlist.is_global_enabled() is True
    assert allowlist.is_simulation_default() is True
    
    # Check supported actions
    policies = allowlist.get_all_policies()
    assert "restart_service" in policies["actions"]
    assert "reset_connections" in policies["actions"]

def test_allowlist_action_permissions():
    allowlist = RemediationAllowlist()
    
    # restart_service allows stateless services
    assert allowlist.is_service_allowed("restart_service", "order-api") is True
    assert allowlist.is_service_allowed("restart_service", "checkout-api") is True
    assert allowlist.is_service_allowed("restart_service", "product-api") is True
    assert allowlist.is_service_allowed("restart_service", "auth-service") is True
    assert allowlist.is_service_allowed("restart_service", "postgresql") is False  # Stateful DB not allowed for restart

    # reset_connections allows postgresql and caller services
    assert allowlist.is_service_allowed("reset_connections", "postgresql") is True
    assert allowlist.is_service_allowed("reset_connections", "order-api") is True
    assert allowlist.is_service_allowed("reset_connections", "redis") is False

    # Disallowed/non-existent action
    assert allowlist.is_service_allowed("arbitrary_action", "order-api") is False

def test_allowlist_parameter_validation():
    allowlist = RemediationAllowlist()

    # Valid parameters for restart_service
    valid, msg = allowlist.validate_parameters("restart_service", {"grace_period_seconds": 15})
    assert valid is True

    # Out of range parameter
    valid_low, msg_low = allowlist.validate_parameters("restart_service", {"grace_period_seconds": 0})
    assert valid_low is False
    assert "below minimum" in msg_low

    valid_high, msg_high = allowlist.validate_parameters("restart_service", {"grace_period_seconds": 120})
    assert valid_high is False
    assert "exceeds maximum" in msg_high

    # Invalid parameter type
    valid_type, msg_type = allowlist.validate_parameters("restart_service", {"grace_period_seconds": "invalid_string"})
    assert valid_type is False

    # Unrecognized parameter
    valid_unknown, msg_unknown = allowlist.validate_parameters("restart_service", {"unknown_param": 10})
    assert valid_unknown is False
    assert "Unrecognized parameter" in msg_unknown
