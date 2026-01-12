"""
Workflow State Management

Manages the deterministic workflow state stored in .eliza/workflow_state.json.
This state tracks which steps have been completed and enforces the workflow order.

State is stored per-workspace and persists across sessions.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class WorkflowStep(str, Enum):
    """Workflow steps in execution order."""
    INIT = "INIT"
    CHECK_CREDENTIALS = "CHECK_CREDENTIALS"
    REQUEST_CREDENTIALS = "REQUEST_CREDENTIALS"
    WRITE_ENV_FILE = "WRITE_ENV_FILE"
    DETECT_INTENT = "DETECT_INTENT"
    SEARCH_FUNCTIONS = "SEARCH_FUNCTIONS"
    CREATE_ARTIFACT = "CREATE_ARTIFACT"
    STATIC_VALIDATION = "STATIC_VALIDATION"
    READY_TO_WRITE = "READY_TO_WRITE"
    RUNTIME_VALIDATION = "RUNTIME_VALIDATION"
    RETRY_LOOP = "RETRY_LOOP"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class WorkflowStatus(str, Enum):
    """Status values for workflow responses."""
    NEED_CREDENTIALS = "NEED_CREDENTIALS"
    NEED_ENV_FILE = "NEED_ENV_FILE"
    SEARCHING = "SEARCHING"
    CREATING = "CREATING"
    VALIDATING = "VALIDATING"
    READY_TO_WRITE = "READY_TO_WRITE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RETRY = "RETRY"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# Step completion requirements
MANDATORY_STEPS = [
    WorkflowStep.CHECK_CREDENTIALS,
    WorkflowStep.WRITE_ENV_FILE,
    WorkflowStep.SEARCH_FUNCTIONS,
    WorkflowStep.CREATE_ARTIFACT,
    WorkflowStep.STATIC_VALIDATION,
]

# Step order for validation
STEP_ORDER = [
    WorkflowStep.INIT,
    WorkflowStep.CHECK_CREDENTIALS,
    WorkflowStep.REQUEST_CREDENTIALS,
    WorkflowStep.WRITE_ENV_FILE,
    WorkflowStep.DETECT_INTENT,
    WorkflowStep.SEARCH_FUNCTIONS,
    WorkflowStep.CREATE_ARTIFACT,
    WorkflowStep.STATIC_VALIDATION,
    WorkflowStep.READY_TO_WRITE,
    WorkflowStep.RUNTIME_VALIDATION,
    WorkflowStep.RETRY_LOOP,
    WorkflowStep.COMPLETE,
]


def get_state_file_path(workspace_path: str) -> str:
    """Get the path to the workflow state file for a workspace."""
    eliza_dir = os.path.join(workspace_path, ".eliza")
    return os.path.join(eliza_dir, "workflow_state.json")


def create_empty_state(workspace_path: str) -> Dict[str, Any]:
    """Create a new empty workflow state."""
    return {
        "version": "1.0",
        "session_id": str(uuid.uuid4()),
        "workspace_path": workspace_path,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "current_step": WorkflowStep.INIT.value,
        "steps_completed": [],
        "credentials": {
            "jwt_provided": False,
            "agent_id": None,
            "initiative_id": None,
            "env": "QA",
            "env_file_written": False
        },
        "intent": {
            "detected_intent": None,
            "user_requirement": None,
            "discovered_functions": [],
            "required_functions": [],
            "optional_functions": []
        },
        "artifact": {
            "type": None,  # "nugget", "agent", "function"
            "code": None,
            "file_path": None,
            "validated": False
        },
        "retry_state": {
            "attempt": 0,
            "max_attempts": 3,
            "errors": []
        },
        "pending_write": {
            "file_path": None,
            "content": None,
            "validated": False
        }
    }


def load_state(workspace_path: str) -> Optional[Dict[str, Any]]:
    """
    Load workflow state from disk.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        State dict or None if no state exists
    """
    state_file = get_state_file_path(workspace_path)

    if not os.path.exists(state_file):
        return None

    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_state(workspace_path: str, state: Dict[str, Any]) -> bool:
    """
    Save workflow state to disk.

    Args:
        workspace_path: Path to the workspace directory
        state: State dict to save

    Returns:
        True if saved successfully
    """
    state_file = get_state_file_path(workspace_path)
    eliza_dir = os.path.dirname(state_file)

    # Create .eliza directory if needed
    os.makedirs(eliza_dir, exist_ok=True)

    # Update timestamp
    state["updated_at"] = datetime.utcnow().isoformat()

    try:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except IOError:
        return False


def get_or_create_state(workspace_path: str) -> Dict[str, Any]:
    """
    Get existing state or create new one.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        State dict (existing or new)
    """
    state = load_state(workspace_path)
    if state is None:
        state = create_empty_state(workspace_path)
        save_state(workspace_path, state)
    return state


def update_step(
    workspace_path: str,
    step: WorkflowStep,
    status: str = "passed",
    result: Any = None
) -> Dict[str, Any]:
    """
    Mark a step as completed and optionally store its result.

    Args:
        workspace_path: Path to the workspace directory
        step: The step that was completed
        status: "passed" or "failed"
        result: Optional result data from the step

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    # Add to completed steps
    step_record = {
        "step": step.value,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    if result is not None:
        step_record["result"] = result

    # Check if step already recorded
    existing_steps = [s["step"] for s in state["steps_completed"]]
    if step.value not in existing_steps:
        state["steps_completed"].append(step_record)

    # Update current step
    state["current_step"] = step.value

    save_state(workspace_path, state)
    return state


def set_current_step(workspace_path: str, step: WorkflowStep) -> Dict[str, Any]:
    """
    Set the current step without marking it complete.

    Args:
        workspace_path: Path to the workspace directory
        step: The current step

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    state["current_step"] = step.value
    save_state(workspace_path, state)
    return state


def is_step_completed(state: Dict[str, Any], step: WorkflowStep) -> bool:
    """Check if a step has been completed."""
    return any(
        s["step"] == step.value and s["status"] == "passed"
        for s in state.get("steps_completed", [])
    )


def get_completed_steps(state: Dict[str, Any]) -> List[str]:
    """Get list of completed step names."""
    return [
        s["step"] for s in state.get("steps_completed", [])
        if s["status"] == "passed"
    ]


def are_prerequisites_met(state: Dict[str, Any], step: WorkflowStep) -> bool:
    """
    Check if all prerequisite steps for a given step are completed.

    Args:
        state: Current workflow state
        step: The step to check prerequisites for

    Returns:
        True if all prerequisites are met
    """
    step_index = STEP_ORDER.index(step) if step in STEP_ORDER else -1

    if step_index <= 0:
        return True  # No prerequisites for INIT or unknown steps

    # Check all mandatory steps before this one
    for prev_step in STEP_ORDER[:step_index]:
        if prev_step in MANDATORY_STEPS and not is_step_completed(state, prev_step):
            # REQUEST_CREDENTIALS and DETECT_INTENT are optional
            if prev_step not in [WorkflowStep.REQUEST_CREDENTIALS, WorkflowStep.DETECT_INTENT]:
                return False

    return True


def get_missing_steps(state: Dict[str, Any]) -> List[str]:
    """
    Get list of mandatory steps that haven't been completed.

    Args:
        state: Current workflow state

    Returns:
        List of missing step names
    """
    completed = set(get_completed_steps(state))
    missing = []

    for step in MANDATORY_STEPS:
        if step.value not in completed:
            missing.append(step.value)

    return missing


def update_credentials(
    workspace_path: str,
    jwt_token: Optional[str] = None,
    agent_id: Optional[str] = None,
    initiative_id: Optional[str] = None,
    env: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update credentials in state.

    Args:
        workspace_path: Path to the workspace directory
        jwt_token: JWT token (stored as boolean, not the actual token)
        agent_id: Agent UUID
        initiative_id: Initiative ID
        env: Environment (DEV, QA, PROD)

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    if jwt_token is not None:
        state["credentials"]["jwt_provided"] = bool(jwt_token)
    if agent_id is not None:
        state["credentials"]["agent_id"] = agent_id
    if initiative_id is not None:
        state["credentials"]["initiative_id"] = initiative_id
    if env is not None:
        state["credentials"]["env"] = env

    save_state(workspace_path, state)
    return state


def update_intent(
    workspace_path: str,
    detected_intent: Optional[str] = None,
    user_requirement: Optional[str] = None,
    discovered_functions: Optional[List[str]] = None,
    required_functions: Optional[List[str]] = None,
    optional_functions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update intent detection results in state.

    Args:
        workspace_path: Path to the workspace directory
        detected_intent: The detected intent name
        user_requirement: Original user requirement
        discovered_functions: All discovered function names
        required_functions: Required function names
        optional_functions: Optional function names

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    if detected_intent is not None:
        state["intent"]["detected_intent"] = detected_intent
    if user_requirement is not None:
        state["intent"]["user_requirement"] = user_requirement
    if discovered_functions is not None:
        state["intent"]["discovered_functions"] = discovered_functions
    if required_functions is not None:
        state["intent"]["required_functions"] = required_functions
    if optional_functions is not None:
        state["intent"]["optional_functions"] = optional_functions

    save_state(workspace_path, state)
    return state


def update_artifact(
    workspace_path: str,
    artifact_type: Optional[str] = None,
    code: Optional[str] = None,
    file_path: Optional[str] = None,
    validated: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update artifact (nugget/agent/function) in state.

    Args:
        workspace_path: Path to the workspace directory
        artifact_type: Type of artifact ("nugget", "agent", "function")
        code: The generated code
        file_path: Path where the artifact will be written
        validated: Whether static validation passed

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    if artifact_type is not None:
        state["artifact"]["type"] = artifact_type
    if code is not None:
        state["artifact"]["code"] = code
    if file_path is not None:
        state["artifact"]["file_path"] = file_path
    if validated is not None:
        state["artifact"]["validated"] = validated

    save_state(workspace_path, state)
    return state


def update_pending_write(
    workspace_path: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    validated: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update pending write information.

    Args:
        workspace_path: Path to the workspace directory
        file_path: Path to write the file
        content: Content to write
        validated: Whether the content is validated

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    if file_path is not None:
        state["pending_write"]["file_path"] = file_path
    if content is not None:
        state["pending_write"]["content"] = content
    if validated is not None:
        state["pending_write"]["validated"] = validated

    save_state(workspace_path, state)
    return state


def add_retry_error(workspace_path: str, error_message: str, fix_suggestion: str = "") -> Dict[str, Any]:
    """
    Add an error to the retry state.

    Args:
        workspace_path: Path to the workspace directory
        error_message: The error message
        fix_suggestion: Suggested fix for the error

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    state["retry_state"]["attempt"] += 1
    state["retry_state"]["errors"].append({
        "attempt": state["retry_state"]["attempt"],
        "error": error_message,
        "fix_suggestion": fix_suggestion,
        "timestamp": datetime.utcnow().isoformat()
    })

    save_state(workspace_path, state)
    return state


def can_retry(state: Dict[str, Any]) -> bool:
    """Check if more retry attempts are allowed."""
    return state["retry_state"]["attempt"] < state["retry_state"]["max_attempts"]


def reset_state(workspace_path: str) -> Dict[str, Any]:
    """
    Reset workflow state to start fresh.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        New empty state dict
    """
    state = create_empty_state(workspace_path)
    save_state(workspace_path, state)
    return state


def validate_state_for_write(workspace_path: str) -> tuple[bool, str]:
    """
    Validate that all prerequisites are met for file writing.

    This is used by the pre_write_code hook to block writes
    if the workflow state is incomplete.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        Tuple of (is_valid, error_message)
    """
    state = load_state(workspace_path)

    if state is None:
        return False, "No workflow state found. Use eliza_workflow tool first."

    # Check mandatory steps
    missing = get_missing_steps(state)
    if missing:
        return False, f"Incomplete workflow. Missing steps: {', '.join(missing)}"

    # Check .env file
    if not state["credentials"].get("env_file_written"):
        return False, "No .env file written. Credentials must be saved first."

    # Check pending write is validated
    if not state["pending_write"].get("validated"):
        return False, "Pending write has not been validated."

    return True, ""


def mark_env_file_written(workspace_path: str) -> Dict[str, Any]:
    """Mark that the .env file has been written."""
    state = get_or_create_state(workspace_path)
    state["credentials"]["env_file_written"] = True
    save_state(workspace_path, state)
    return state
