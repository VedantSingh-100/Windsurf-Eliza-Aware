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

    Handles both v1.0 and v2.0 state structures:
    - v1.0: Updates state.steps_completed and state.current_step
    - v2.0: Updates active artifact's steps_completed and workflow_step

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

    # Handle v2.0 state (per-artifact tracking)
    if state.get("version") == "2.0":
        # Get active artifact
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                # Update artifact's steps
                existing_steps = [s["step"] for s in artifact.get("steps_completed", [])]
                if step.value not in existing_steps:
                    artifact["steps_completed"].append(step_record)
                artifact["workflow_step"] = step.value
                artifact["updated_at"] = datetime.utcnow().isoformat()

                # Update artifact status based on step
                if step == WorkflowStep.COMPLETE:
                    artifact["status"] = "completed"
                elif step == WorkflowStep.FAILED:
                    artifact["status"] = "failed"
                elif step in [WorkflowStep.CREATE_ARTIFACT, WorkflowStep.STATIC_VALIDATION]:
                    artifact["status"] = "in_progress"

        save_state(workspace_path, state)
        return state

    # Handle v1.0 state (root-level tracking)
    existing_steps = [s["step"] for s in state.get("steps_completed", [])]
    if step.value not in existing_steps:
        if "steps_completed" not in state:
            state["steps_completed"] = []
        state["steps_completed"].append(step_record)

    # Update current step
    state["current_step"] = step.value

    save_state(workspace_path, state)
    return state


def set_current_step(workspace_path: str, step: WorkflowStep) -> Dict[str, Any]:
    """
    Set the current step without marking it complete.

    Handles both v1.0 and v2.0 state:
    - v1.0: Sets state.current_step
    - v2.0: Sets active artifact's workflow_step

    Args:
        workspace_path: Path to the workspace directory
        step: The current step

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    # v2.0: Update active artifact
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                artifact["workflow_step"] = step.value
                artifact["updated_at"] = datetime.utcnow().isoformat()
        save_state(workspace_path, state)
        return state

    # v1.0: Update root level
    state["current_step"] = step.value
    save_state(workspace_path, state)
    return state


def get_current_step(state: Dict[str, Any]) -> str:
    """
    Get the current workflow step.

    Handles both v1.0 and v2.0 state:
    - v1.0: Returns state.current_step
    - v2.0: Returns active artifact's workflow_step

    Args:
        state: Current workflow state

    Returns:
        Current step as string
    """
    # v2.0: Get from active artifact
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return artifact.get("workflow_step", WorkflowStep.INIT.value)
        return WorkflowStep.INIT.value

    # v1.0: Get from root level
    return state.get("current_step", WorkflowStep.INIT.value)


def is_step_completed(state: Dict[str, Any], step: WorkflowStep) -> bool:
    """
    Check if a step has been completed.

    Handles both v1.0 and v2.0 state:
    - v1.0: Checks state.steps_completed
    - v2.0: Checks active artifact's steps_completed
    """
    # v2.0: Check active artifact
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return any(
                    s["step"] == step.value and s["status"] == "passed"
                    for s in artifact.get("steps_completed", [])
                )
        return False

    # v1.0: Check root-level steps
    return any(
        s["step"] == step.value and s["status"] == "passed"
        for s in state.get("steps_completed", [])
    )


def get_completed_steps(state: Dict[str, Any]) -> List[str]:
    """
    Get list of completed step names.

    Handles both v1.0 and v2.0 state.
    """
    # v2.0: Get from active artifact
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return [
                    s["step"] for s in artifact.get("steps_completed", [])
                    if s["status"] == "passed"
                ]
        return []

    # v1.0: Get from root level
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

    Handles both v1.0 and v2.0 state:
    - v1.0: Updates state.intent
    - v2.0: Updates active artifact's intent

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

    # v2.0: Update active artifact's intent
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                if detected_intent is not None:
                    artifact["intent"]["detected_intent"] = detected_intent
                if user_requirement is not None:
                    artifact["intent"]["user_requirement"] = user_requirement
                if discovered_functions is not None:
                    artifact["intent"]["discovered_functions"] = discovered_functions
                if required_functions is not None:
                    artifact["intent"]["required_functions"] = required_functions
                if optional_functions is not None:
                    artifact["intent"]["optional_functions"] = optional_functions
                artifact["updated_at"] = datetime.utcnow().isoformat()
        save_state(workspace_path, state)
        return state

    # v1.0: Update root-level intent
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

    Handles both v1.0 and v2.0 state:
    - v1.0: Updates state.artifact
    - v2.0: Updates active artifact's artifact_data

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

    # v2.0: Update active artifact
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                if artifact_type is not None:
                    artifact["type"] = artifact_type
                if code is not None:
                    artifact["artifact_data"]["code"] = code
                if file_path is not None:
                    artifact["file_path"] = file_path
                if validated is not None:
                    artifact["artifact_data"]["validated"] = validated
                artifact["updated_at"] = datetime.utcnow().isoformat()
        save_state(workspace_path, state)
        return state

    # v1.0: Update root-level artifact
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

    Handles both v1.0 and v2.0 state:
    - v1.0: Updates state.pending_write
    - v2.0: Updates active artifact's pending_write

    Args:
        workspace_path: Path to the workspace directory
        file_path: Path to write the file
        content: Content to write
        validated: Whether the content is validated

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    # v2.0: Update active artifact's pending write
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                if file_path is not None:
                    artifact["pending_write"]["file_path"] = file_path
                    artifact["file_path"] = file_path  # Also update main file_path
                if content is not None:
                    artifact["pending_write"]["content"] = content
                if validated is not None:
                    artifact["pending_write"]["validated"] = validated
                artifact["updated_at"] = datetime.utcnow().isoformat()
        save_state(workspace_path, state)
        return state

    # v1.0: Update root-level pending_write
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

    Handles both v1.0 and v2.0 state.

    Args:
        workspace_path: Path to the workspace directory
        error_message: The error message
        fix_suggestion: Suggested fix for the error

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    # v2.0: Update active artifact's retry state
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            return update_artifact_retry(workspace_path, active_id, error_message, fix_suggestion)
        return state

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
    """
    Check if more retry attempts are allowed.

    Handles both v1.0 and v2.0 state.
    """
    # v2.0: Check active artifact's retry state
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return can_artifact_retry(artifact)
        return True  # No artifact = can retry

    # v1.0: Check root-level retry state
    retry_state = state.get("retry_state", {})
    return retry_state.get("attempt", 0) < retry_state.get("max_attempts", 3)


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


# =============================================================================
# WORKSPACE RESOLUTION AND LAZY CREDENTIAL INITIALIZATION
# =============================================================================

def resolve_workspace_path(arguments: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve workspace path - NO AUTO-DISCOVERY from parent directories.

    Each workspace is unique and isolated. This function does NOT search
    parent directories to find .eliza/ folders.

    Resolution order:
    1. If workspace_path is explicitly provided in arguments, use it
    2. Check if CWD has .eliza/workflow_state.json (NOT parents!)
    3. If not found, return error asking user to provide workspace_path

    Args:
        arguments: Tool arguments dict, may contain 'workspace_path' key

    Returns:
        Tuple of (workspace_path, error_message)
        - If workspace found: (path, None)
        - If not found: (None, error_message)
    """
    # 1. Explicit argument takes priority
    if arguments.get("workspace_path"):
        path = arguments["workspace_path"]
        if os.path.isdir(path):
            return path, None
        return None, f"Workspace path not found: {path}. Please provide a valid directory path."

    # 2. Check ONLY the current working directory - NO PARENT TRAVERSAL
    # Each workspace must be unique - no auto-discovery from parent directories
    cwd = os.getcwd()
    eliza_dir = os.path.join(cwd, ".eliza")
    state_file = os.path.join(eliza_dir, "workflow_state.json")

    if os.path.exists(state_file):
        return cwd, None  # Found state in CWD only

    # 3. Discovery failed - ask user
    return None, (
        "Could not auto-detect workspace. Please provide the workspace_path parameter.\n"
        "Example: workspace_path='/path/to/your/project'"
    )


def _validate_jwt_format_basic(jwt: str) -> tuple[bool, str]:
    """
    Basic JWT format validation (local copy to avoid circular imports).

    Checks:
    - Token is not too short
    - Token is not a placeholder
    - Token has three dot-separated parts (JWT format)

    Args:
        jwt: The JWT token string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not jwt or len(jwt) < 10:
        return False, "JWT token is too short"

    # Check for placeholders
    placeholders = ["{YOUR_JWT}", "jwt_token", "{JWT}", "YOUR_JWT_HERE", "<jwt>", "your_jwt"]
    if any(p.lower() in jwt.lower() for p in placeholders):
        return False, "JWT appears to be a placeholder. Please provide a real token."

    # Basic JWT format check (three base64 parts separated by dots)
    parts = jwt.split(".")
    if len(parts) != 3:
        return False, "JWT must have three parts separated by dots"

    return True, ""


def write_env_file(
    workspace_path: str,
    jwt_token: str,
    agent_id: Optional[str] = None,
    initiative_id: Optional[str] = None,
    env: str = "QA"
) -> bool:
    """
    Write .env file to workspace with credentials.

    Creates or overwrites the .env file in the workspace root directory.
    This file is used by hooks and API calls to authenticate.

    Args:
        workspace_path: Path to the workspace directory
        jwt_token: JWT token for authentication
        agent_id: Agent UUID (optional)
        initiative_id: Initiative ID (optional)
        env: Environment (DEV, QA, PROD), defaults to QA

    Returns:
        True if file was written successfully, False otherwise
    """
    env_path = os.path.join(workspace_path, ".env")
    content = f"""# Eliza Credentials - Auto-generated
# DO NOT COMMIT THIS FILE

ELIZA_JWT_TOKEN={jwt_token}
ELIZA_AGENT_ID={agent_id or ''}
ELIZA_INITIATIVE_ID={initiative_id or ''}
ELIZA_ENV={env}
"""
    try:
        with open(env_path, 'w') as f:
            f.write(content)
        return True
    except IOError:
        return False


def read_env_file(workspace_path: str) -> Dict[str, str]:
    """
    Read credentials from .env file in workspace.

    This is the CENTRALIZED function for reading stored credentials.
    All tools should use this (via ensure_credentials) instead of
    manually parsing .env files.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        Dict with keys: jwt_token, agent_id, initiative_id, env
        Missing values will be empty strings
    """
    env_path = os.path.join(workspace_path, ".env")
    result = {
        "jwt_token": "",
        "agent_id": "",
        "initiative_id": "",
        "env": "QA"
    }

    if not os.path.exists(env_path):
        return result

    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "ELIZA_JWT_TOKEN":
                        result["jwt_token"] = value
                    elif key == "ELIZA_AGENT_ID":
                        result["agent_id"] = value
                    elif key == "ELIZA_INITIATIVE_ID":
                        result["initiative_id"] = value
                    elif key == "ELIZA_ENV":
                        result["env"] = value or "QA"
    except IOError:
        pass

    return result


def ensure_credentials(
    workspace_path: str,
    jwt_token: Optional[str] = None,
    agent_id: Optional[str] = None,
    initiative_id: Optional[str] = None,
    env: str = "QA"
) -> tuple[bool, Dict[str, Any], str]:
    """
    Ensure credentials exist for a workspace, creating minimal state if needed.

    This is the CENTRALIZED credential management function. All tools should
    use this to get credentials instead of manually reading .env files.

    This function implements lazy credential initialization:
    - If workflow state exists, read actual credentials from .env and return
    - If no state exists but jwt_token is provided, create minimal state
    - If no state exists and no jwt_token, return error

    The minimal state created has workflow_step="CREDENTIALS_ONLY" which
    is sufficient for READ/EXECUTE operations but not for CREATE operations.

    Args:
        workspace_path: Path to the workspace directory
        jwt_token: JWT token (required if no existing state)
        agent_id: Agent UUID (optional)
        initiative_id: Initiative ID (optional)
        env: Environment (DEV, QA, PROD), defaults to QA

    Returns:
        Tuple of (success, credentials_dict, error_message)
        - success: True if credentials are available
        - credentials_dict: Dict with ACTUAL values: jwt_token, agent_id, initiative_id, env
        - error_message: Error string if success is False

    Example:
        success, creds, error = ensure_credentials(workspace_path, jwt_token="...")
        if success:
            jwt = creds["jwt_token"]  # The ACTUAL JWT token
            agent_id = creds["agent_id"]
    """
    state = load_state(workspace_path)

    if state is not None:
        # State exists - read ACTUAL credentials from .env file
        env_creds = read_env_file(workspace_path)

        # Check if we have valid credentials stored
        if env_creds.get("jwt_token"):
            # Return actual credentials from .env file
            return True, {
                "jwt_token": env_creds["jwt_token"],
                "agent_id": env_creds.get("agent_id") or agent_id or "",
                "initiative_id": env_creds.get("initiative_id") or initiative_id or "",
                "env": env_creds.get("env") or env,
                "jwt_provided": True
            }, ""

        # State exists but no JWT in .env - need jwt_token to update
        if not jwt_token:
            return False, {}, (
                "Workflow state exists but JWT token not found in .env file. "
                "Please provide jwt_token parameter."
            )

    # No state or state needs credentials
    if not jwt_token:
        return False, {}, (
            "No workflow state found. Please provide jwt_token parameter, "
            "or run eliza_workflow(action='start') to initialize credentials."
        )

    # Validate JWT format
    valid, error = _validate_jwt_format_basic(jwt_token)
    if not valid:
        return False, {}, f"Invalid JWT token: {error}"

    # Create minimal state with CREDENTIALS_ONLY step
    minimal_state = {
        "version": "2.0",
        "session_id": str(uuid.uuid4()),
        "workspace_path": workspace_path,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "workflow_step": "CREDENTIALS_ONLY",  # Special step for lazy init

        # Shared credentials
        "credentials": {
            "jwt_provided": True,
            "agent_id": agent_id,
            "initiative_id": initiative_id,
            "env": env,
            "env_file_written": True,
            "validated_at": datetime.utcnow().isoformat()
        },

        # Empty artifacts array (no CREATE workflow run)
        "artifacts": [],
        "active_artifact_id": None,

        # Mark as created via lazy init
        "created_via": "lazy_init",

        # Discovery not done
        "discovery": {
            "completed": False,
            "completed_at": None,
            "discovered_files": [],
            "patterns_used": []
        }
    }

    # Save state
    save_state(workspace_path, minimal_state)

    # Write .env file
    write_env_file(workspace_path, jwt_token, agent_id, initiative_id, env)

    # Return ACTUAL credentials including the jwt_token
    return True, {
        "jwt_token": jwt_token,
        "agent_id": agent_id or "",
        "initiative_id": initiative_id or "",
        "env": env,
        "jwt_provided": True
    }, ""


def is_credentials_only_state(state: Dict[str, Any]) -> bool:
    """
    Check if state was created via lazy initialization (credentials only).

    States created via ensure_credentials() have workflow_step="CREDENTIALS_ONLY"
    or created_via="lazy_init". These states are sufficient for READ/EXECUTE
    operations but not for CREATE operations which require full workflow.

    Args:
        state: The workflow state dict

    Returns:
        True if state is credentials-only (not full workflow)
    """
    if state is None:
        return False

    # Check for CREDENTIALS_ONLY step
    if state.get("workflow_step") == "CREDENTIALS_ONLY":
        return True

    # Check for lazy_init marker
    if state.get("created_via") == "lazy_init":
        return True

    # For v2.0, also check if no artifacts exist
    if state.get("version") == "2.0":
        if not state.get("artifacts") and state.get("credentials", {}).get("jwt_provided"):
            return True

    return False


# =============================================================================
# V2.0 MULTI-ARTIFACT STATE MANAGEMENT
# =============================================================================

def create_empty_state_v2(workspace_path: str) -> Dict[str, Any]:
    """
    Create a new empty workflow state with v2.0 multi-artifact support.

    V2.0 supports multiple artifacts with independent workflow states,
    shared credentials, and auto-discovery of existing files.
    """
    return {
        "version": "2.0",
        "session_id": str(uuid.uuid4()),
        "workspace_path": workspace_path,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),

        # Shared credentials (validated once, reused for all artifacts)
        "credentials": {
            "jwt_provided": False,
            "agent_id": None,
            "initiative_id": None,
            "env": "QA",
            "env_file_written": False,
            "validated_at": None
        },

        # Multi-artifact support
        "artifacts": [],
        "active_artifact_id": None,

        # Discovery state
        "discovery": {
            "completed": False,
            "completed_at": None,
            "discovered_files": [],
            "patterns_used": []
        },

        # Migration tracking
        "_migrated_from_v1": False
    }


def create_artifact_state(
    artifact_type: str,
    label: str,
    file_path: Optional[str] = None,
    discovered: bool = False
) -> Dict[str, Any]:
    """
    Create a new artifact state entry.

    Each artifact has its own workflow step, retry state, and pending write.
    This enables parallel/independent artifact workflows.

    Args:
        artifact_type: Type of artifact ("nugget", "agent", "function")
        label: Human-readable label for the artifact
        file_path: Path to the artifact file (optional)
        discovered: True if found via discovery, False if created new

    Returns:
        New artifact state dict
    """
    return {
        "artifact_id": str(uuid.uuid4()),
        "type": artifact_type,
        "label": label,
        "file_path": file_path,

        # Per-artifact workflow tracking
        "workflow_step": WorkflowStep.INIT.value,
        "status": "pending",  # pending, in_progress, completed, failed, deployed
        "discovered": discovered,

        # Per-artifact retry state (independent from other artifacts)
        "retry_state": {
            "attempt": 0,
            "max_attempts": 3,
            "errors": []
        },

        # Per-artifact pending write
        "pending_write": {
            "file_path": None,
            "content": None,
            "validated": False
        },

        # Intent/requirement for this artifact
        "intent": {
            "user_requirement": None,
            "detected_intent": None,
            "discovered_functions": [],
            "required_functions": [],
            "optional_functions": []
        },

        # Generated code for this artifact
        "artifact_data": {
            "code": None,
            "validated": False,
            "nugget_id": None,
            "function_id": None,
            "agent_id": None
        },

        # Step history for this artifact
        "steps_completed": [],

        # Timestamps
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# ARTIFACT CRUD OPERATIONS
# =============================================================================

def add_artifact(
    workspace_path: str,
    artifact_type: str,
    label: str,
    file_path: Optional[str] = None,
    discovered: bool = False
) -> tuple[Dict[str, Any], str]:
    """
    Add a new artifact to the workflow state.

    Args:
        workspace_path: Path to the workspace directory
        artifact_type: Type of artifact ("nugget", "agent", "function")
        label: Human-readable label
        file_path: Path to the artifact file (optional)
        discovered: True if found via discovery

    Returns:
        Tuple of (updated state, artifact_id)
    """
    state = get_or_create_state(workspace_path)

    # Ensure v2.0 state
    if state.get("version") != "2.0":
        state = migrate_v1_to_v2(workspace_path)

    # Create new artifact
    artifact = create_artifact_state(artifact_type, label, file_path, discovered)
    artifact_id = artifact["artifact_id"]

    # Add to artifacts array
    state["artifacts"].append(artifact)

    save_state(workspace_path, state)
    return state, artifact_id


def get_artifact(state: Dict[str, Any], artifact_id: str) -> Optional[Dict[str, Any]]:
    """
    Get artifact by ID from state.

    Args:
        state: Current workflow state
        artifact_id: UUID of the artifact

    Returns:
        Artifact dict or None if not found
    """
    for artifact in state.get("artifacts", []):
        if artifact.get("artifact_id") == artifact_id:
            return artifact
    return None


def get_artifact_by_path(state: Dict[str, Any], file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get artifact by file path from state.

    Used by hooks to look up artifact state when validating a specific file.

    Args:
        state: Current workflow state
        file_path: Path to the artifact file

    Returns:
        Artifact dict or None if not found
    """
    # Normalize path for comparison
    norm_path = os.path.normpath(file_path)

    for artifact in state.get("artifacts", []):
        artifact_path = artifact.get("file_path")
        if artifact_path:
            if os.path.normpath(artifact_path) == norm_path:
                return artifact
        # Also check pending_write path
        pending_path = artifact.get("pending_write", {}).get("file_path")
        if pending_path:
            if os.path.normpath(pending_path) == norm_path:
                return artifact

    return None


def get_artifact_by_label(state: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    """
    Get artifact by label from state.

    Args:
        state: Current workflow state
        label: Label of the artifact (case-insensitive)

    Returns:
        Artifact dict or None if not found
    """
    label_lower = label.lower()
    for artifact in state.get("artifacts", []):
        if artifact.get("label", "").lower() == label_lower:
            return artifact
    return None


def get_active_artifact(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get currently active artifact.

    Args:
        state: Current workflow state

    Returns:
        Active artifact dict or None if no active artifact
    """
    active_id = state.get("active_artifact_id")
    if active_id:
        return get_artifact(state, active_id)
    return None


def set_active_artifact(workspace_path: str, artifact_id: str) -> Dict[str, Any]:
    """
    Set the active artifact for workflow operations.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact to make active

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    # Verify artifact exists
    artifact = get_artifact(state, artifact_id)
    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    state["active_artifact_id"] = artifact_id
    save_state(workspace_path, state)
    return state


def list_artifacts(
    state: Dict[str, Any],
    status: Optional[str] = None,
    artifact_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all artifacts, optionally filtered by status or type.

    Args:
        state: Current workflow state
        status: Filter by status (optional)
        artifact_type: Filter by type (optional)

    Returns:
        List of artifact dicts
    """
    artifacts = state.get("artifacts", [])

    if status:
        artifacts = [a for a in artifacts if a.get("status") == status]

    if artifact_type:
        artifacts = [a for a in artifacts if a.get("type") == artifact_type]

    return artifacts


def remove_artifact(workspace_path: str, artifact_id: str) -> Dict[str, Any]:
    """
    Remove an artifact from tracking (does not delete files).

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact to remove

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)

    state["artifacts"] = [
        a for a in state.get("artifacts", [])
        if a.get("artifact_id") != artifact_id
    ]

    # Clear active if removed
    if state.get("active_artifact_id") == artifact_id:
        state["active_artifact_id"] = None

    save_state(workspace_path, state)
    return state


# =============================================================================
# PER-ARTIFACT UPDATE OPERATIONS
# =============================================================================

def update_artifact_step(
    workspace_path: str,
    artifact_id: str,
    step: WorkflowStep,
    status: str = "passed",
    result: Any = None
) -> Dict[str, Any]:
    """
    Update a specific artifact's workflow step.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact
        step: The step that was completed
        status: "passed" or "failed"
        result: Optional result data

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    artifact = get_artifact(state, artifact_id)

    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    # Add to completed steps
    step_record = {
        "step": step.value,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    if result is not None:
        step_record["result"] = result

    # Check if step already recorded
    existing_steps = [s["step"] for s in artifact.get("steps_completed", [])]
    if step.value not in existing_steps:
        artifact["steps_completed"].append(step_record)

    # Update current step and status
    artifact["workflow_step"] = step.value
    artifact["updated_at"] = datetime.utcnow().isoformat()

    # Update artifact status based on step
    if step == WorkflowStep.COMPLETE:
        artifact["status"] = "completed"
    elif step == WorkflowStep.FAILED:
        artifact["status"] = "failed"
    elif step in [WorkflowStep.CREATE_ARTIFACT, WorkflowStep.STATIC_VALIDATION]:
        artifact["status"] = "in_progress"

    save_state(workspace_path, state)
    return state


def update_artifact_intent(
    workspace_path: str,
    artifact_id: str,
    user_requirement: Optional[str] = None,
    detected_intent: Optional[str] = None,
    discovered_functions: Optional[List[str]] = None,
    required_functions: Optional[List[str]] = None,
    optional_functions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update intent detection results for a specific artifact.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact
        user_requirement: Original user requirement
        detected_intent: The detected intent name
        discovered_functions: All discovered function names
        required_functions: Required function names
        optional_functions: Optional function names

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    artifact = get_artifact(state, artifact_id)

    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    if user_requirement is not None:
        artifact["intent"]["user_requirement"] = user_requirement
    if detected_intent is not None:
        artifact["intent"]["detected_intent"] = detected_intent
    if discovered_functions is not None:
        artifact["intent"]["discovered_functions"] = discovered_functions
    if required_functions is not None:
        artifact["intent"]["required_functions"] = required_functions
    if optional_functions is not None:
        artifact["intent"]["optional_functions"] = optional_functions

    artifact["updated_at"] = datetime.utcnow().isoformat()
    save_state(workspace_path, state)
    return state


def update_artifact_code(
    workspace_path: str,
    artifact_id: str,
    code: Optional[str] = None,
    validated: Optional[bool] = None,
    nugget_id: Optional[str] = None,
    function_id: Optional[str] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update generated code for a specific artifact.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact
        code: The generated code
        validated: Whether static validation passed
        nugget_id: API-returned nugget ID after deployment
        function_id: API-returned function ID
        agent_id: API-returned agent ID

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    artifact = get_artifact(state, artifact_id)

    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    if code is not None:
        artifact["artifact_data"]["code"] = code
    if validated is not None:
        artifact["artifact_data"]["validated"] = validated
    if nugget_id is not None:
        artifact["artifact_data"]["nugget_id"] = nugget_id
    if function_id is not None:
        artifact["artifact_data"]["function_id"] = function_id
    if agent_id is not None:
        artifact["artifact_data"]["agent_id"] = agent_id

    artifact["updated_at"] = datetime.utcnow().isoformat()
    save_state(workspace_path, state)
    return state


def update_artifact_pending_write(
    workspace_path: str,
    artifact_id: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    validated: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update pending write for a specific artifact.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact
        file_path: Path to write the file
        content: Content to write
        validated: Whether the content is validated

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    artifact = get_artifact(state, artifact_id)

    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    if file_path is not None:
        artifact["pending_write"]["file_path"] = file_path
        # Also update artifact's file_path
        artifact["file_path"] = file_path
    if content is not None:
        artifact["pending_write"]["content"] = content
    if validated is not None:
        artifact["pending_write"]["validated"] = validated

    artifact["updated_at"] = datetime.utcnow().isoformat()
    save_state(workspace_path, state)
    return state


def update_artifact_retry(
    workspace_path: str,
    artifact_id: str,
    error_message: str,
    fix_suggestion: str = ""
) -> Dict[str, Any]:
    """
    Add retry error to a specific artifact.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact
        error_message: The error message
        fix_suggestion: Suggested fix for the error

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    artifact = get_artifact(state, artifact_id)

    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    artifact["retry_state"]["attempt"] += 1
    artifact["retry_state"]["errors"].append({
        "attempt": artifact["retry_state"]["attempt"],
        "error": error_message,
        "fix_suggestion": fix_suggestion,
        "timestamp": datetime.utcnow().isoformat()
    })

    artifact["updated_at"] = datetime.utcnow().isoformat()
    save_state(workspace_path, state)
    return state


def can_artifact_retry(artifact: Dict[str, Any]) -> bool:
    """
    Check if more retry attempts are allowed for an artifact.

    Args:
        artifact: The artifact dict

    Returns:
        True if retries are still allowed
    """
    retry_state = artifact.get("retry_state", {})
    return retry_state.get("attempt", 0) < retry_state.get("max_attempts", 3)


def reset_artifact_retry(workspace_path: str, artifact_id: str) -> Dict[str, Any]:
    """
    Reset retry state for a specific artifact.

    Args:
        workspace_path: Path to the workspace directory
        artifact_id: UUID of the artifact

    Returns:
        Updated state dict
    """
    state = get_or_create_state(workspace_path)
    artifact = get_artifact(state, artifact_id)

    if artifact is None:
        raise ValueError(f"Artifact {artifact_id} not found")

    artifact["retry_state"] = {
        "attempt": 0,
        "max_attempts": 3,
        "errors": []
    }

    artifact["updated_at"] = datetime.utcnow().isoformat()
    save_state(workspace_path, state)
    return state


# =============================================================================
# MIGRATION V1 -> V2
# =============================================================================

def migrate_v1_to_v2(workspace_path: str) -> Dict[str, Any]:
    """
    Migrate v1.0 state to v2.0 format.

    Preserves:
    - Credentials (shared across artifacts)
    - Current artifact (becomes first entry in artifacts array)
    - Completed steps

    The original v1.0 state is preserved in _v1_backup for safety.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        Migrated v2.0 state dict
    """
    state = load_state(workspace_path)

    if state is None:
        return create_empty_state_v2(workspace_path)

    if state.get("version") == "2.0":
        return state  # Already v2.0

    # Create v2.0 state
    new_state = create_empty_state_v2(workspace_path)

    # Preserve session_id and timestamps
    new_state["session_id"] = state.get("session_id", new_state["session_id"])
    new_state["created_at"] = state.get("created_at", new_state["created_at"])

    # Copy credentials (shared)
    old_creds = state.get("credentials", {})
    new_state["credentials"]["jwt_provided"] = old_creds.get("jwt_provided", False)
    new_state["credentials"]["agent_id"] = old_creds.get("agent_id")
    new_state["credentials"]["initiative_id"] = old_creds.get("initiative_id")
    new_state["credentials"]["env"] = old_creds.get("env", "QA")
    new_state["credentials"]["env_file_written"] = old_creds.get("env_file_written", False)

    # Migrate single artifact to artifacts array
    old_artifact = state.get("artifact", {})
    old_intent = state.get("intent", {})
    old_pending = state.get("pending_write", {})
    old_retry = state.get("retry_state", {})
    old_steps = state.get("steps_completed", [])
    current_step = state.get("current_step", WorkflowStep.INIT.value)

    # Only migrate if there's actual artifact data
    has_artifact = (
        old_artifact.get("type") or
        old_artifact.get("code") or
        old_intent.get("user_requirement") or
        old_pending.get("file_path")
    )

    if has_artifact:
        # Determine label
        label = (
            old_intent.get("detected_intent") or
            old_intent.get("user_requirement", "")[:50] or
            "migrated_artifact"
        )

        # Create artifact from v1 data
        artifact = create_artifact_state(
            artifact_type=old_artifact.get("type", "nugget"),
            label=label,
            file_path=old_artifact.get("file_path") or old_pending.get("file_path"),
            discovered=False
        )

        # Copy v1 data to artifact
        artifact["intent"] = {
            "user_requirement": old_intent.get("user_requirement"),
            "detected_intent": old_intent.get("detected_intent"),
            "discovered_functions": old_intent.get("discovered_functions", []),
            "required_functions": old_intent.get("required_functions", []),
            "optional_functions": old_intent.get("optional_functions", [])
        }

        artifact["artifact_data"] = {
            "code": old_artifact.get("code"),
            "validated": old_artifact.get("validated", False),
            "nugget_id": None,
            "function_id": None,
            "agent_id": None
        }

        artifact["pending_write"] = {
            "file_path": old_pending.get("file_path"),
            "content": old_pending.get("content"),
            "validated": old_pending.get("validated", False)
        }

        artifact["retry_state"] = {
            "attempt": old_retry.get("attempt", 0),
            "max_attempts": old_retry.get("max_attempts", 3),
            "errors": old_retry.get("errors", [])
        }

        artifact["steps_completed"] = old_steps
        artifact["workflow_step"] = current_step

        # Determine status from step
        if current_step == WorkflowStep.COMPLETE.value:
            artifact["status"] = "completed"
        elif current_step == WorkflowStep.FAILED.value:
            artifact["status"] = "failed"
        elif current_step != WorkflowStep.INIT.value:
            artifact["status"] = "in_progress"

        new_state["artifacts"].append(artifact)
        new_state["active_artifact_id"] = artifact["artifact_id"]

    # Mark as migrated and backup original
    new_state["_migrated_from_v1"] = True
    new_state["_v1_backup"] = state

    save_state(workspace_path, new_state)
    return new_state


# =============================================================================
# BACKWARDS COMPATIBILITY
# =============================================================================

def get_legacy_artifact(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get artifact in v1.0-compatible format.

    Returns active artifact's data structured like v1.0 state.
    Used by hooks that haven't been updated yet.

    Args:
        state: Current workflow state (v1 or v2)

    Returns:
        Dict with artifact, intent, pending_write, retry_state keys
    """
    if state.get("version") != "2.0":
        # Already v1 format
        return {
            "artifact": state.get("artifact", {}),
            "intent": state.get("intent", {}),
            "pending_write": state.get("pending_write", {}),
            "retry_state": state.get("retry_state", {}),
            "current_step": state.get("current_step")
        }

    # Get active artifact from v2
    artifact = get_active_artifact(state)
    if artifact is None:
        return None

    return {
        "artifact": artifact.get("artifact_data", {}),
        "intent": artifact.get("intent", {}),
        "pending_write": artifact.get("pending_write", {}),
        "retry_state": artifact.get("retry_state", {}),
        "current_step": artifact.get("workflow_step")
    }


def validate_state_for_write_v2(
    workspace_path: str,
    file_path: Optional[str] = None
) -> tuple[bool, str]:
    """
    Validate that all prerequisites are met for file writing (v2.0).

    In v2.0: Looks up artifact by file_path, validates that specific artifact.
    Falls back to active artifact if no file_path provided.

    Args:
        workspace_path: Path to the workspace directory
        file_path: Path of file being written (optional)

    Returns:
        Tuple of (is_valid, error_message)
    """
    state = load_state(workspace_path)

    if state is None:
        return False, "No workflow state found. Use eliza_workflow tool first."

    # Check credentials (shared)
    if not state.get("credentials", {}).get("env_file_written"):
        return False, "No .env file written. Credentials must be saved first."

    if state.get("version") == "2.0":
        # V2.0: Look up artifact by file_path
        artifact = None
        if file_path:
            artifact = get_artifact_by_path(state, file_path)
        if artifact is None:
            artifact = get_active_artifact(state)

        if artifact is None:
            return False, "No artifact found for this file. Run eliza_workflow(action='discover') or action='start'."

        # Check artifact's pending_write is validated
        if not artifact.get("pending_write", {}).get("validated"):
            return False, f"Artifact '{artifact.get('label')}' has not been validated. Run eliza_workflow(action='continue')."

        return True, ""
    else:
        # V1.0: Use existing logic
        return validate_state_for_write(workspace_path)
