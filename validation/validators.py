"""
Input Validators

Centralized validation for all input parameters before API calls.
This module provides strict validation to catch errors early.

VALIDATION POLICY:
- Strict mode (default): Block on any validation error
- All validators return ValidatorResult with success/failure and actionable errors
"""

import re
import base64
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Valid environment values
VALID_ENVIRONMENTS = {"DEV", "TEST", "QA", "PROD"}

# Valid parameter types for nugget params
VALID_PARAM_TYPES = {"string", "number", "boolean", "object", "array"}


@dataclass
class ValidationError:
    """Represents a validation error with actionable fix."""
    field: str
    message: str
    fix: Optional[str] = None


@dataclass
class ValidatorResult:
    """Result of validation with success/failure and errors."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)


# =============================================================================
# INDIVIDUAL VALIDATORS
# =============================================================================

def validate_jwt_token(token: str) -> ValidatorResult:
    """
    Validate JWT token format.

    Checks:
    - Non-empty
    - 3 dot-separated parts (header.payload.signature)
    - Each part is valid base64 (URL-safe)

    Note: Does NOT verify the signature - that's the API's responsibility.
    """
    errors = []

    if not token:
        errors.append(ValidationError(
            field="jwt_token",
            message="JWT token is required",
            fix="Provide your Eliza JWT token"
        ))
        return ValidatorResult(valid=False, errors=errors)

    if not isinstance(token, str):
        errors.append(ValidationError(
            field="jwt_token",
            message="JWT token must be a string",
            fix="Provide JWT token as a string"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Check for placeholder values
    placeholders = ["{YOUR_JWT}", "YOUR_JWT", "jwt_token", "{jwt_token}"]
    if token in placeholders or token.startswith("{"):
        errors.append(ValidationError(
            field="jwt_token",
            message="JWT token appears to be a placeholder",
            fix="Provide your actual Eliza JWT token, not a placeholder"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # JWT should have 3 parts: header.payload.signature
    parts = token.split(".")
    if len(parts) != 3:
        errors.append(ValidationError(
            field="jwt_token",
            message=f"JWT token should have 3 parts separated by dots, found {len(parts)}",
            fix="Ensure the JWT token is complete and correctly formatted"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Validate each part is base64 (URL-safe variant)
    for i, part in enumerate(parts):
        part_name = ["header", "payload", "signature"][i]
        # Add padding if needed for base64 decode
        padded = part + "=" * (4 - len(part) % 4) if len(part) % 4 else part
        # Replace URL-safe characters
        padded = padded.replace("-", "+").replace("_", "/")
        try:
            base64.b64decode(padded)
        except Exception:
            errors.append(ValidationError(
                field="jwt_token",
                message=f"JWT {part_name} is not valid base64",
                fix="Ensure the JWT token is not truncated or corrupted"
            ))
            return ValidatorResult(valid=False, errors=errors)

    return ValidatorResult(valid=True)


def validate_agent_id(agent_id: str) -> ValidatorResult:
    """
    Validate agent_id is a valid UUID format.

    Checks:
    - Non-empty
    - UUID v4 format: 8-4-4-4-12 hex characters
    """
    errors = []

    if not agent_id:
        errors.append(ValidationError(
            field="agent_id",
            message="Agent ID is required",
            fix="Provide the UUID of the agent"
        ))
        return ValidatorResult(valid=False, errors=errors)

    if not isinstance(agent_id, str):
        errors.append(ValidationError(
            field="agent_id",
            message="Agent ID must be a string",
            fix="Provide agent_id as a string"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Check for placeholder values
    placeholders = ["{AGENT_ID}", "AGENT_ID", "agent_id", "{agent_id}", "your-agent-id"]
    if agent_id.lower() in [p.lower() for p in placeholders]:
        errors.append(ValidationError(
            field="agent_id",
            message="Agent ID appears to be a placeholder",
            fix="Provide the actual agent UUID"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # UUID v4 format: 8-4-4-4-12 hex characters
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, agent_id.lower()):
        errors.append(ValidationError(
            field="agent_id",
            message=f"Agent ID is not a valid UUID format: {agent_id}",
            fix="Use UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        ))
        return ValidatorResult(valid=False, errors=errors)

    return ValidatorResult(valid=True)


def validate_initiative_id(initiative_id: str) -> ValidatorResult:
    """
    Validate initiative_id format.

    Checks:
    - Non-empty
    - Starts with 'ELZI-'
    - User ID portion is alphanumeric
    """
    errors = []

    if not initiative_id:
        errors.append(ValidationError(
            field="initiative_id",
            message="Initiative ID is required",
            fix="Provide your initiative ID (format: ELZI-{userid})"
        ))
        return ValidatorResult(valid=False, errors=errors)

    if not isinstance(initiative_id, str):
        errors.append(ValidationError(
            field="initiative_id",
            message="Initiative ID must be a string",
            fix="Provide initiative_id as a string"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Check for default/placeholder values
    if initiative_id.upper() == "ELZ-00000":
        errors.append(ValidationError(
            field="initiative_id",
            message="Using default initiative ID 'ELZ-00000' - this will fail",
            fix="Use your personal initiative ID: ELZI-{your_userid}"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Check format: ELZI-{userid}
    if not initiative_id.upper().startswith("ELZI-"):
        errors.append(ValidationError(
            field="initiative_id",
            message=f"Initiative ID should start with 'ELZI-', got: {initiative_id}",
            fix="Format: ELZI-{your_userid} (e.g., ELZI-XFMLC5G)"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Check user ID portion is alphanumeric
    user_id = initiative_id[5:]  # Remove 'ELZI-' prefix
    if not user_id or not re.match(r'^[A-Za-z0-9]+$', user_id):
        errors.append(ValidationError(
            field="initiative_id",
            message=f"User ID portion '{user_id}' should be alphanumeric",
            fix="Format: ELZI-{alphanumeric_userid}"
        ))
        return ValidatorResult(valid=False, errors=errors)

    return ValidatorResult(valid=True)


def validate_env(env: str) -> ValidatorResult:
    """
    Validate environment against allowed values.

    Checks:
    - Must be one of: DEV, TEST, QA, PROD
    """
    errors = []

    if not env:
        # Default to QA, not an error
        return ValidatorResult(valid=True)

    if not isinstance(env, str):
        errors.append(ValidationError(
            field="env",
            message="Environment must be a string",
            fix="Use one of: DEV, TEST, QA, PROD"
        ))
        return ValidatorResult(valid=False, errors=errors)

    if env.upper() not in VALID_ENVIRONMENTS:
        errors.append(ValidationError(
            field="env",
            message=f"Invalid environment '{env}'",
            fix=f"Use one of: {', '.join(sorted(VALID_ENVIRONMENTS))}"
        ))
        return ValidatorResult(valid=False, errors=errors)

    return ValidatorResult(valid=True)


def validate_discovered_functions(functions: List[str]) -> ValidatorResult:
    """
    Validate all functions exist in EZ_FUNCTION_INDEX.

    Checks:
    - Each function name exists in the index
    - Warns if function status is DEPRECATED or NEEDS_CONFIG

    Returns warnings (not errors) for deprecated/config-needed functions.
    """
    from search.index import EZ_FUNCTION_INDEX

    errors = []
    warnings = []

    if not functions:
        # Empty list is not an error (could be PYTHON_STATIC)
        return ValidatorResult(valid=True)

    if not isinstance(functions, list):
        errors.append(ValidationError(
            field="discovered_functions",
            message="discovered_functions must be a list",
            fix="Provide a list of function names, e.g., ['ezMail', 'ezInternetSearch']"
        ))
        return ValidatorResult(valid=False, errors=errors)

    invalid_functions = []
    deprecated_functions = []
    config_needed_functions = []

    for func in functions:
        if not isinstance(func, str):
            errors.append(ValidationError(
                field="discovered_functions",
                message=f"Function name must be a string, got: {type(func).__name__}",
                fix="Provide function names as strings"
            ))
            continue

        if func not in EZ_FUNCTION_INDEX:
            invalid_functions.append(func)
        else:
            status = EZ_FUNCTION_INDEX[func].get("status", "WORKS")
            if status == "DEPRECATED":
                deprecated_functions.append(func)
            elif status == "NEEDS_CONFIG":
                config_needed_functions.append(func)

    if invalid_functions:
        errors.append(ValidationError(
            field="discovered_functions",
            message=f"Unknown functions: {', '.join(invalid_functions)}",
            fix="Use search_ez_functions to find valid function names"
        ))

    if deprecated_functions:
        warnings.append(ValidationError(
            field="discovered_functions",
            message=f"Deprecated functions: {', '.join(deprecated_functions)}",
            fix="Consider using alternative functions"
        ))

    if config_needed_functions:
        warnings.append(ValidationError(
            field="discovered_functions",
            message=f"Functions requiring configuration: {', '.join(config_needed_functions)}",
            fix="Ensure secrets/config are set up for these functions"
        ))

    return ValidatorResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_nugget_params(params: List[Dict[str, Any]]) -> ValidatorResult:
    """
    Validate params array schema for create_nugget.

    Required fields: paramNameKey, paramType, paramDescription
    Optional fields: optional (bool)
    Valid paramTypes: string, number, boolean, object, array
    """
    errors = []
    warnings = []

    if not params:
        # Empty params is valid
        return ValidatorResult(valid=True)

    if not isinstance(params, list):
        errors.append(ValidationError(
            field="params",
            message="params must be a list",
            fix="Provide params as a list of objects"
        ))
        return ValidatorResult(valid=False, errors=errors)

    for i, param in enumerate(params):
        if not isinstance(param, dict):
            errors.append(ValidationError(
                field=f"params[{i}]",
                message=f"Parameter {i} must be an object",
                fix="Each param should be: {paramNameKey, paramType, paramDescription}"
            ))
            continue

        # Check required fields
        required_fields = ["paramNameKey", "paramType", "paramDescription"]
        for field in required_fields:
            if field not in param:
                errors.append(ValidationError(
                    field=f"params[{i}].{field}",
                    message=f"Missing required field '{field}' in parameter {i}",
                    fix=f"Add '{field}' to the parameter definition"
                ))

        # Validate paramType
        if "paramType" in param:
            param_type = param["paramType"]
            if param_type not in VALID_PARAM_TYPES:
                errors.append(ValidationError(
                    field=f"params[{i}].paramType",
                    message=f"Invalid paramType '{param_type}'",
                    fix=f"Use one of: {', '.join(sorted(VALID_PARAM_TYPES))}"
                ))

        # Validate optional field if present
        if "optional" in param and not isinstance(param["optional"], bool):
            warnings.append(ValidationError(
                field=f"params[{i}].optional",
                message="'optional' field should be a boolean",
                fix="Use true or false for 'optional'"
            ))

    return ValidatorResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_email(email: str) -> ValidatorResult:
    """
    Validate email format for code generation.

    Checks:
    - Basic email format (x@y.z)
    - No special characters that could break JavaScript
    """
    errors = []

    if not email:
        # Empty email is valid (might not be needed)
        return ValidatorResult(valid=True)

    if not isinstance(email, str):
        errors.append(ValidationError(
            field="email",
            message="Email must be a string",
            fix="Provide email as a string"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Basic email format check
    email_pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    if not re.match(email_pattern, email):
        errors.append(ValidationError(
            field="email",
            message=f"Invalid email format: {email}",
            fix="Provide a valid email address (e.g., user@example.com)"
        ))
        return ValidatorResult(valid=False, errors=errors)

    # Check for characters that could break JavaScript strings
    dangerous_chars = ['"', "'", "\\", "\n", "\r", "<", ">"]
    for char in dangerous_chars:
        if char in email:
            errors.append(ValidationError(
                field="email",
                message=f"Email contains invalid character: {repr(char)}",
                fix="Use a simple email address without special characters"
            ))
            return ValidatorResult(valid=False, errors=errors)

    return ValidatorResult(valid=True)


# =============================================================================
# COMPOSITE VALIDATORS
# =============================================================================

def validate_create_agent_inputs(
    jwt_token: str,
    initiative_id: str,
    env: str = "QA"
) -> ValidatorResult:
    """
    Run all validations for create_*_agent tools.

    Validates: jwt_token, initiative_id, env
    Fails fast on first ERROR, collects all issues.
    """
    all_errors = []
    all_warnings = []

    # Validate JWT token
    jwt_result = validate_jwt_token(jwt_token)
    all_errors.extend(jwt_result.errors)
    all_warnings.extend(jwt_result.warnings)

    # Validate initiative_id
    init_result = validate_initiative_id(initiative_id)
    all_errors.extend(init_result.errors)
    all_warnings.extend(init_result.warnings)

    # Validate env
    env_result = validate_env(env)
    all_errors.extend(env_result.errors)
    all_warnings.extend(env_result.warnings)

    return ValidatorResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings
    )


def validate_create_nugget_inputs(
    jwt_token: str,
    agent_id: str,
    discovered_functions: List[str] = None,
    params: List[Dict] = None,
    env: str = "QA",
    email: str = None
) -> ValidatorResult:
    """
    Run all validations for create_nugget tool.

    Validates: jwt_token, agent_id, discovered_functions, params, env, email
    Fails fast on first ERROR, collects all issues.
    """
    all_errors = []
    all_warnings = []

    # Validate JWT token
    jwt_result = validate_jwt_token(jwt_token)
    all_errors.extend(jwt_result.errors)
    all_warnings.extend(jwt_result.warnings)

    # Validate agent_id
    agent_result = validate_agent_id(agent_id)
    all_errors.extend(agent_result.errors)
    all_warnings.extend(agent_result.warnings)

    # Validate discovered_functions
    if discovered_functions:
        func_result = validate_discovered_functions(discovered_functions)
        all_errors.extend(func_result.errors)
        all_warnings.extend(func_result.warnings)

    # Validate params
    if params:
        params_result = validate_nugget_params(params)
        all_errors.extend(params_result.errors)
        all_warnings.extend(params_result.warnings)

    # Validate env
    env_result = validate_env(env)
    all_errors.extend(env_result.errors)
    all_warnings.extend(env_result.warnings)

    # Validate email
    if email:
        email_result = validate_email(email)
        all_errors.extend(email_result.errors)
        all_warnings.extend(email_result.warnings)

    return ValidatorResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings
    )


def validate_common_inputs(
    jwt_token: str,
    agent_id: str,
    env: str = "QA"
) -> ValidatorResult:
    """
    Common validation for CRUD operations.

    Validates: jwt_token, agent_id, env
    """
    all_errors = []
    all_warnings = []

    # Validate JWT token
    jwt_result = validate_jwt_token(jwt_token)
    all_errors.extend(jwt_result.errors)
    all_warnings.extend(jwt_result.warnings)

    # Validate agent_id
    agent_result = validate_agent_id(agent_id)
    all_errors.extend(agent_result.errors)
    all_warnings.extend(agent_result.warnings)

    # Validate env
    env_result = validate_env(env)
    all_errors.extend(env_result.errors)
    all_warnings.extend(env_result.warnings)

    return ValidatorResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_validation_errors(result: ValidatorResult) -> str:
    """Format validation result as a readable string."""
    if result.valid:
        return "Validation passed"

    lines = []

    if result.errors:
        lines.append("ERRORS:")
        for error in result.errors:
            lines.append(f"  - {error.field}: {error.message}")
            if error.fix:
                lines.append(f"    Fix: {error.fix}")

    if result.warnings:
        lines.append("\nWARNINGS:")
        for warning in result.warnings:
            lines.append(f"  - {warning.field}: {warning.message}")
            if warning.fix:
                lines.append(f"    Fix: {warning.fix}")

    return "\n".join(lines)
