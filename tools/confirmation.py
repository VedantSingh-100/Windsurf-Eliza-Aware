"""
Confirmation System for Destructive Operations

Implements a deterministic, code-enforced confirmation mechanism for
mutation operations (delete, update, disable). Tools REFUSE to execute
without proper confirmation token.

Flow:
1. Tool called without confirm_token → returns confirmation request
2. Cascade shows user the impact and asks for confirmation
3. User confirms → Cascade calls with confirm_token
4. Tool validates token and executes

Usage:
    from tools.confirmation import require_confirmation, requires_confirmation

    @require_confirmation("This will permanently delete the agent")
    def handle_delete_agent(arguments):
        ...
"""

import uuid
import time
import json
import functools
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, asdict


# =============================================================================
# CONFIGURATION
# =============================================================================

TOKEN_EXPIRY_SECONDS = 300  # 5 minutes

# Operations that require confirmation
# Format: tool_name -> True (all operations) or list of specific operations
CONFIRMATION_REQUIRED_OPERATIONS: Dict[str, Union[bool, List[str]]] = {
    # Direct CRUD tools (always require confirmation)
    "delete_agent": True,
    "delete_nugget": True,
    "delete_function": True,
    "update_agent": True,
    "update_nugget": True,

    # Operation tools with specific operations requiring confirmation
    "agent_crud": ["delete", "update", "disable"],
    "nugget_crud": ["delete", "update"],
    "function_crud": ["delete"],
    "document_crud": ["delete"],
    "chunk_operations": ["delete"],
    "access_operations": ["remove_agent_access", "remove_auth_access"],
    "identity_operations": ["delete"],
    "hashes_operations": ["delete"],
    "ideas_operations": ["delete"],
}

# Impact messages for operations
IMPACT_MESSAGES: Dict[str, str] = {
    # Delete operations
    "delete_agent": "Permanently delete agent '{target}' and all its nuggets/functions",
    "delete_nugget": "Permanently delete nugget '{target}' from agent",
    "delete_function": "Remove function '{target}' from agent",
    "agent_crud.delete": "Permanently delete agent '{target}' and all its data",
    "nugget_crud.delete": "Permanently delete nugget '{target}'",
    "function_crud.delete": "Remove function '{target}' from agent",
    "document_crud.delete": "Permanently delete document '{target}'",
    "chunk_operations.delete": "Delete chunk '{target}' from document",
    "identity_operations.delete": "Remove identity '{target}' from agent",
    "hashes_operations.delete": "Delete hash '{target}'",
    "ideas_operations.delete": "Delete idea '{target}'",

    # Update operations
    "update_agent": "Modify agent '{target}' configuration",
    "update_nugget": "Modify nugget '{target}' configuration",
    "agent_crud.update": "Modify agent '{target}' configuration",
    "agent_crud.disable": "Disable agent '{target}' - it will stop responding to requests",
    "nugget_crud.update": "Modify nugget '{target}' configuration",

    # Access operations
    "access_operations.remove_agent_access": "Remove agent access for '{target}'",
    "access_operations.remove_auth_access": "Remove authentication access for '{target}'",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PendingConfirmation:
    """Represents a pending confirmation request."""
    token: str
    action: str
    target: str
    target_id: str
    params: Dict[str, Any]
    impact: str
    created_at: float
    expires_at: float

    def is_expired(self) -> bool:
        """Check if the confirmation has expired."""
        return time.time() > self.expires_at

    def to_response(self) -> Dict[str, Any]:
        """Convert to response format for the tool."""
        return {
            "status": "confirmation_required",
            "action": self.action,
            "target": self.target,
            "target_id": self.target_id,
            "impact": self.impact,
            "confirm_token": self.token,
            "expires_in_seconds": max(0, int(self.expires_at - time.time())),
            "message": f"⚠️ CONFIRMATION REQUIRED: {self.impact}. "
                      f"To proceed, call this tool again with confirm_token='{self.token}'"
        }


# In-memory store for pending confirmations
_PENDING_CONFIRMATIONS: Dict[str, PendingConfirmation] = {}


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def requires_confirmation(tool_name: str, operation: str = None) -> bool:
    """
    Check if a tool/operation requires confirmation.

    Args:
        tool_name: Name of the tool (e.g., "delete_agent", "agent_crud")
        operation: Optional operation name for operation tools (e.g., "delete")

    Returns:
        True if confirmation is required
    """
    config = CONFIRMATION_REQUIRED_OPERATIONS.get(tool_name)

    if config is None:
        return False

    if config is True:
        return True

    if isinstance(config, list) and operation:
        return operation in config

    return False


def get_impact_message(tool_name: str, operation: str = None) -> str:
    """Get the impact message for a tool/operation."""
    if operation:
        key = f"{tool_name}.{operation}"
    else:
        key = tool_name

    return IMPACT_MESSAGES.get(key, f"Execute {key} operation")


def get_target_description(arguments: Dict[str, Any]) -> str:
    """
    Extract a human-readable target description from arguments.

    Looks for common identifier fields in order of preference.
    """
    # Try to find a name first
    for name_field in ["name", "agent_name", "nugget_name", "function_name"]:
        if name_field in arguments and arguments[name_field]:
            return str(arguments[name_field])

    # Fall back to ID fields
    for id_field in ["agent_id", "nugget_id", "function_id", "document_id",
                     "chunk_id", "identity_id", "hash_id", "idea_id", "id"]:
        if id_field in arguments and arguments[id_field]:
            return str(arguments[id_field])

    return "unknown"


def get_target_id(arguments: Dict[str, Any]) -> str:
    """Extract the target ID from arguments."""
    for id_field in ["agent_id", "nugget_id", "function_id", "document_id",
                     "chunk_id", "identity_id", "hash_id", "idea_id", "id"]:
        if id_field in arguments and arguments[id_field]:
            return str(arguments[id_field])
    return "unknown"


def create_confirmation_request(
    action: str,
    target: str,
    target_id: str,
    params: Dict[str, Any],
    impact: str
) -> Dict[str, Any]:
    """
    Generate a confirmation request with unique token.

    Args:
        action: The action being confirmed (e.g., "delete_agent")
        target: Human-readable target description
        target_id: The ID of the target resource
        params: Original parameters for the operation
        impact: Impact message describing what will happen

    Returns:
        Confirmation request response dict
    """
    # Clean up expired confirmations
    _cleanup_expired_confirmations()

    # Generate unique token
    token = str(uuid.uuid4())

    # Format impact message with target
    formatted_impact = impact.format(target=target)

    # Create pending confirmation
    now = time.time()
    confirmation = PendingConfirmation(
        token=token,
        action=action,
        target=target,
        target_id=target_id,
        params=params,
        impact=formatted_impact,
        created_at=now,
        expires_at=now + TOKEN_EXPIRY_SECONDS
    )

    # Store it
    _PENDING_CONFIRMATIONS[token] = confirmation

    return confirmation.to_response()


def validate_confirmation(token: str, action: str) -> tuple[bool, Optional[str]]:
    """
    Validate a confirmation token.

    Args:
        token: The confirmation token to validate
        action: The action being confirmed (must match original)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not token:
        return False, "No confirmation token provided"

    confirmation = _PENDING_CONFIRMATIONS.get(token)

    if not confirmation:
        return False, "Invalid confirmation token - not found or already used"

    if confirmation.is_expired():
        # Clean up expired token
        del _PENDING_CONFIRMATIONS[token]
        return False, "Confirmation token has expired (5 minute limit)"

    if confirmation.action != action:
        return False, f"Token action mismatch: expected '{confirmation.action}', got '{action}'"

    # Token is valid - remove it (one-time use)
    del _PENDING_CONFIRMATIONS[token]

    return True, None


def get_pending_confirmation(token: str) -> Optional[PendingConfirmation]:
    """Get details of a pending confirmation."""
    confirmation = _PENDING_CONFIRMATIONS.get(token)
    if confirmation and not confirmation.is_expired():
        return confirmation
    return None


def _cleanup_expired_confirmations():
    """Remove expired confirmations from the store."""
    now = time.time()
    expired_tokens = [
        token for token, conf in _PENDING_CONFIRMATIONS.items()
        if conf.expires_at < now
    ]
    for token in expired_tokens:
        del _PENDING_CONFIRMATIONS[token]


# =============================================================================
# DECORATOR
# =============================================================================

def require_confirmation(impact_message: str = None):
    """
    Decorator that enforces confirmation for a handler.

    The decorated handler will:
    1. Return a confirmation request if no confirm_token is provided
    2. Validate the token and reject if invalid/expired
    3. Execute the actual operation if token is valid

    Args:
        impact_message: Custom impact message (uses default if not provided)

    Usage:
        @require_confirmation("This will permanently delete the agent")
        def handle_delete_agent(arguments):
            ...

        @require_confirmation()  # Uses default message
        async def handle_delete_nugget(arguments):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Determine action name from function name
        action_name = func.__name__
        if action_name.startswith("handle_"):
            action_name = action_name[7:]  # Remove "handle_" prefix

        @functools.wraps(func)
        def sync_wrapper(arguments: Dict[str, Any]) -> Any:
            confirm_token = arguments.get("confirm_token")

            if not confirm_token:
                # Generate confirmation request
                target = get_target_description(arguments)
                target_id = get_target_id(arguments)
                impact = impact_message or get_impact_message(action_name)

                return create_confirmation_request(
                    action=action_name,
                    target=target,
                    target_id=target_id,
                    params={k: v for k, v in arguments.items() if k != "confirm_token"},
                    impact=impact
                )

            # Validate token
            is_valid, error = validate_confirmation(confirm_token, action_name)
            if not is_valid:
                return {
                    "status": "error",
                    "error": error,
                    "hint": "Request a new confirmation by calling without confirm_token"
                }

            # Execute the actual operation
            return func(arguments)

        @functools.wraps(func)
        async def async_wrapper(arguments: Dict[str, Any]) -> Any:
            confirm_token = arguments.get("confirm_token")

            if not confirm_token:
                # Generate confirmation request
                target = get_target_description(arguments)
                target_id = get_target_id(arguments)
                impact = impact_message or get_impact_message(action_name)

                return create_confirmation_request(
                    action=action_name,
                    target=target,
                    target_id=target_id,
                    params={k: v for k, v in arguments.items() if k != "confirm_token"},
                    impact=impact
                )

            # Validate token
            is_valid, error = validate_confirmation(confirm_token, action_name)
            if not is_valid:
                return {
                    "status": "error",
                    "error": error,
                    "hint": "Request a new confirmation by calling without confirm_token"
                }

            # Execute the actual operation
            return await func(arguments)

        # Return appropriate wrapper based on whether func is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# HELPER FOR OPERATION TOOLS
# =============================================================================

def check_operation_confirmation(
    category: str,
    operation: str,
    arguments: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Check if an operation requires confirmation and handle it.

    For use in operation tools (category_router.py).

    Args:
        category: The operation category (e.g., "agent_crud")
        operation: The specific operation (e.g., "delete")
        arguments: The operation arguments

    Returns:
        None if no confirmation needed or token is valid
        Confirmation request dict if confirmation is needed
        Error dict if token is invalid
    """
    if not requires_confirmation(category, operation):
        return None

    confirm_token = arguments.get("confirm_token")
    action_name = f"{category}.{operation}"

    if not confirm_token:
        # Generate confirmation request
        target = get_target_description(arguments)
        target_id = get_target_id(arguments)
        impact = get_impact_message(category, operation)

        return create_confirmation_request(
            action=action_name,
            target=target,
            target_id=target_id,
            params={k: v for k, v in arguments.items() if k != "confirm_token"},
            impact=impact
        )

    # Validate token
    is_valid, error = validate_confirmation(confirm_token, action_name)
    if not is_valid:
        return {
            "status": "error",
            "error": error,
            "hint": "Request a new confirmation by calling without confirm_token"
        }

    # Token is valid, proceed with operation
    return None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "require_confirmation",
    "requires_confirmation",
    "check_operation_confirmation",
    "create_confirmation_request",
    "validate_confirmation",
    "get_pending_confirmation",
    "get_target_description",
    "get_impact_message",
    "CONFIRMATION_REQUIRED_OPERATIONS",
    "IMPACT_MESSAGES",
]
