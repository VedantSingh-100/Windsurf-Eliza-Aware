"""
Validation Module

Centralized input validation for Eliza MCP Server.

All validators return ValidatorResult objects with:
- valid: bool - Whether validation passed
- errors: List[ValidationError] - Blocking errors
- warnings: List[ValidationError] - Non-blocking warnings
"""

from validation.validators import (
    # Data classes
    ValidationError,
    ValidatorResult,

    # Constants
    VALID_ENVIRONMENTS,
    VALID_PARAM_TYPES,

    # Individual validators
    validate_jwt_token,
    validate_agent_id,
    validate_initiative_id,
    validate_env,
    validate_discovered_functions,
    validate_nugget_params,
    validate_email,

    # Composite validators
    validate_create_agent_inputs,
    validate_create_nugget_inputs,
    validate_common_inputs,

    # Helper functions
    format_validation_errors,
)

__all__ = [
    # Data classes
    "ValidationError",
    "ValidatorResult",

    # Constants
    "VALID_ENVIRONMENTS",
    "VALID_PARAM_TYPES",

    # Individual validators
    "validate_jwt_token",
    "validate_agent_id",
    "validate_initiative_id",
    "validate_env",
    "validate_discovered_functions",
    "validate_nugget_params",
    "validate_email",

    # Composite validators
    "validate_create_agent_inputs",
    "validate_create_nugget_inputs",
    "validate_common_inputs",

    # Helper functions
    "format_validation_errors",
]
