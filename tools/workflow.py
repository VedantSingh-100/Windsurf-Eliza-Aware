"""
Eliza Workflow Orchestrator

This is the MAIN entry point for all Eliza development tasks.
It enforces a deterministic workflow that CANNOT be bypassed.

Workflow Phases:
1. INIT → Start new workflow
2. CHECK_CREDENTIALS → Verify JWT and agent_id
3. WRITE_ENV_FILE → Write .env with credentials
4. DETECT_INTENT → Use smart_search to detect user intent
5. SEARCH_FUNCTIONS → Get required ez* functions
6. CREATE_ARTIFACT → Generate nugget/agent/function code
7. STATIC_VALIDATION → Validate code before writing
8. READY_TO_WRITE → Approve file write
9. RUNTIME_VALIDATION → Hook validates after write
10. RETRY_LOOP → If validation fails, retry with fix
11. COMPLETE → Workflow finished successfully

Usage:
    Cascade MUST call eliza_workflow for ANY Eliza task.
    The tool returns the next action Cascade should take.
"""

import os
import re
from typing import Dict, Any, List, Optional

from tools.workflow_state import (
    WorkflowStep,
    WorkflowStatus,
    get_or_create_state,
    update_step,
    update_credentials,
    update_intent,
    update_artifact,
    update_pending_write,
    add_retry_error,
    mark_env_file_written,
    is_step_completed,
    get_missing_steps,
    get_current_step,  # V2.0 compatible
    can_retry,
    reset_state,
    save_state,
    MANDATORY_STEPS,
    # V2.0 multi-artifact functions
    create_empty_state_v2,
    add_artifact,
    get_artifact,
    get_artifact_by_path,
    get_active_artifact,
    set_active_artifact,
    list_artifacts,
    update_artifact_step,
    update_artifact_intent,
    update_artifact_code,
    update_artifact_pending_write,
    update_artifact_retry,
    can_artifact_retry,
    migrate_v1_to_v2,
    # Workspace resolution (smart discovery)
    resolve_workspace_path,
)
from search.search import smart_search, get_function_signatures
from search.index import EZ_FUNCTION_INDEX
from validation.static import validate_code
from tools.discovery import discover_artifacts, sync_discovered_to_state, get_discovery_summary


# =============================================================================
# TOOL DEFINITION
# =============================================================================

WORKFLOW_TOOL = {
    "name": "eliza_workflow",
    "description": """MANDATORY orchestrator for ALL Eliza development tasks.

This tool enforces a deterministic workflow for creating agents, nuggets, and functions.
Cascade MUST use this tool for ANY Eliza-related task - no bypassing allowed.

The tool guides you through each step and tells you exactly what to do next.

V2.0 FEATURES:
- Multi-artifact support: Work on multiple nuggets/agents without losing state
- Auto-discovery: Find existing Eliza files in your workspace
- Shared credentials: Validate once, reuse for all artifacts

Actions:
- start: Begin a new workflow for a NEW artifact (reuses credentials if already validated)
- continue: Continue workflow for active artifact
- retry: Retry after a validation failure
- reset: Reset workflow state completely
- status: Get current workflow status
- discover: Scan workspace for existing Eliza artifacts (nuggets, agents, functions)
- switch: Switch to a different artifact by artifact_id
- list: List all tracked artifacts with their status

Example:
    Call with action="discover" to find existing files
    Call with action="start" and requirement="Create a newsletter agent"
    Follow the returned instructions for each step.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "continue", "retry", "reset", "status", "discover", "switch", "list"],
                "description": "Workflow action to perform"
            },
            "requirement": {
                "type": "string",
                "description": "What the user wants to build (for 'start' action)"
            },
            "workspace_path": {
                "type": "string",
                "description": "Path to workspace directory (defaults to current directory)"
            },
            "artifact_id": {
                "type": "string",
                "description": "Target artifact ID (for 'switch' or 'continue' on specific artifact)"
            },
            "jwt_token": {
                "type": "string",
                "description": "JWT token for authentication"
            },
            "agent_id": {
                "type": "string",
                "description": "Agent UUID"
            },
            "initiative_id": {
                "type": "string",
                "description": "Initiative ID (for agent creation)"
            },
            "env": {
                "type": "string",
                "enum": ["DEV", "TEST", "QA", "PROD"],
                "description": "Environment (defaults to QA)"
            },
            "email": {
                "type": "string",
                "description": "User email address"
            },
            "generated_code": {
                "type": "string",
                "description": "Code generated by Cascade (for validation step)"
            },
            "file_path": {
                "type": "string",
                "description": "File path for the artifact"
            },
            "include_tests": {
                "type": "boolean",
                "description": "Include test files in discovery (default: false)"
            }
        },
        "required": ["action"]
    }
}

WORKFLOW_TOOLS = [WORKFLOW_TOOL]


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_jwt_format(jwt: str) -> tuple[bool, str]:
    """Validate JWT token format."""
    if not jwt or len(jwt) < 10:
        return False, "JWT token is too short"

    # Check for placeholders
    placeholders = ["{YOUR_JWT}", "jwt_token", "{JWT}", "YOUR_JWT_HERE"]
    if any(p.lower() in jwt.lower() for p in placeholders):
        return False, "JWT appears to be a placeholder. Please provide a real token."

    # Basic JWT format check (three base64 parts separated by dots)
    parts = jwt.split(".")
    if len(parts) != 3:
        return False, "JWT must have three parts separated by dots"

    return True, ""


def validate_agent_id_format(agent_id: str) -> tuple[bool, str]:
    """Validate agent ID format (UUID)."""
    if not agent_id:
        return False, "Agent ID is required"

    # Check for placeholders
    placeholders = ["{AGENT_ID}", "agent_id", "{ID}", "YOUR_AGENT_ID"]
    if any(p.lower() in agent_id.lower() for p in placeholders):
        return False, "Agent ID appears to be a placeholder. Please provide a real UUID."

    # UUID format check
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, agent_id.lower()):
        return False, "Agent ID must be a valid UUID format"

    return True, ""


def validate_initiative_id_format(init_id: str) -> tuple[bool, str]:
    """Validate initiative ID format."""
    if not init_id:
        return True, ""  # Optional

    # Check for default/placeholder
    if init_id in ["ELZ-00000", "{INITIATIVE_ID}", "initiative_id"]:
        return False, "Initiative ID appears to be a placeholder"

    # Should start with ELZI- or similar
    if not init_id.startswith("ELZI-") and not init_id.startswith("ELZ-"):
        return False, "Initiative ID should start with ELZI- or ELZ-"

    return True, ""


# =============================================================================
# WORKFLOW HANDLER
# =============================================================================

async def handle_eliza_workflow(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for the eliza_workflow tool.

    This implements the deterministic state machine that enforces
    the Eliza development workflow.

    V2.0: Supports multi-artifact workflows with discover, switch, list actions.
    """
    action = arguments.get("action", "status")

    # Resolve workspace path - smart discovery or explicit parameter
    workspace_path, ws_error = resolve_workspace_path(arguments)
    if ws_error:
        return {
            "status": "WORKSPACE_REQUIRED",
            "message": ws_error,
            "next_step": "Provide workspace_path parameter",
            "example": "eliza_workflow(action='start', workspace_path='/path/to/your/project', ...)"
        }

    # Get or create workflow state (auto-migrates v1 to v2 if needed)
    state = get_or_create_state(workspace_path)

    # Ensure v2.0 state
    if state.get("version") != "2.0":
        state = migrate_v1_to_v2(workspace_path)

    if action == "reset":
        return handle_reset(workspace_path)

    if action == "status":
        return handle_status(state)

    # V2.0 actions
    if action == "discover":
        return await handle_discover(arguments, workspace_path, state)

    if action == "switch":
        return await handle_switch(arguments, workspace_path, state)

    if action == "list":
        return handle_list(state)

    if action == "start":
        return await handle_start(arguments, workspace_path, state)

    if action == "continue":
        return await handle_continue(arguments, workspace_path, state)

    if action == "retry":
        return await handle_retry(arguments, workspace_path, state)

    return {
        "status": "ERROR",
        "message": f"Unknown action: {action}. Use: start, continue, retry, reset, status, discover, switch, list"
    }


def handle_reset(workspace_path: str) -> Dict[str, Any]:
    """Reset workflow state."""
    reset_state(workspace_path)
    return {
        "status": "RESET",
        "message": "Workflow state reset. Call with action='start' to begin.",
        "next_action": "Call eliza_workflow with action='start' and your requirement"
    }


def handle_status(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get current workflow status."""
    # V2.0 status includes multi-artifact info
    if state.get("version") == "2.0":
        active_artifact = get_active_artifact(state)
        artifacts = list_artifacts(state)

        active_info = None
        if active_artifact:
            active_info = {
                "artifact_id": active_artifact["artifact_id"],
                "label": active_artifact["label"],
                "type": active_artifact["type"],
                "workflow_step": active_artifact["workflow_step"],
                "status": active_artifact["status"],
                "retry_attempt": active_artifact["retry_state"]["attempt"]
            }

        return {
            "status": "STATUS",
            "version": "2.0",
            "total_artifacts": len(artifacts),
            "active_artifact": active_info,
            "artifacts_summary": [
                {
                    "artifact_id": a["artifact_id"],
                    "label": a["label"],
                    "type": a["type"],
                    "status": a["status"]
                }
                for a in artifacts
            ],
            "credentials": {
                "jwt_provided": state["credentials"]["jwt_provided"],
                "agent_id": state["credentials"]["agent_id"],
                "env_file_written": state["credentials"]["env_file_written"]
            },
            "discovery_completed": state["discovery"]["completed"],
            "message": f"V2.0: {len(artifacts)} artifacts tracked. Active: {active_artifact['label'] if active_artifact else 'None'}"
        }
    else:
        # V1.0 fallback
        missing = get_missing_steps(state)
        return {
            "status": "STATUS",
            "version": "1.0",
            "current_step": state["current_step"],
            "steps_completed": [s["step"] for s in state["steps_completed"] if s["status"] == "passed"],
            "missing_steps": missing,
            "credentials": {
                "jwt_provided": state["credentials"]["jwt_provided"],
                "agent_id": state["credentials"]["agent_id"],
                "env_file_written": state["credentials"]["env_file_written"]
            },
            "intent": state["intent"],
            "retry_state": state["retry_state"],
            "message": f"Current step: {state['current_step']}. Missing: {missing or 'None'}"
        }


# =============================================================================
# V2.0 ACTION HANDLERS
# =============================================================================

async def handle_discover(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Discover existing Eliza artifacts in workspace.

    Scans for nugget, agent, and function files and registers them
    in the workflow state for tracking.
    """
    include_tests = arguments.get("include_tests", False)

    # Discover artifacts
    discovered = discover_artifacts(workspace_path, include_tests=include_tests)

    # Sync to state
    added_ids, skipped_paths = sync_discovered_to_state(workspace_path, discovered, state)

    # Update discovery state
    state = get_or_create_state(workspace_path)
    state["discovery"]["completed"] = True
    state["discovery"]["completed_at"] = __import__("datetime").datetime.utcnow().isoformat()
    state["discovery"]["discovered_files"] = [d["relative_path"] for d in discovered]
    save_state(workspace_path, state)

    # Get summary
    summary = get_discovery_summary(workspace_path, discovered)

    return {
        "status": "DISCOVERY_COMPLETE",
        "total_found": len(discovered),
        "discovered_count": len(added_ids),  # Alias for backwards compatibility
        "newly_added": len(added_ids),
        "already_tracked": len(skipped_paths),
        "by_type": summary.get("by_type", {}),
        "artifacts": [
            {
                "label": d["label"],
                "type": d["type"],
                "path": d["relative_path"]
            }
            for d in discovered
        ],
        "message": f"Found {len(discovered)} artifacts. Added {len(added_ids)} new, {len(skipped_paths)} already tracked.",
        "next_action": "Call action='list' to see all artifacts, or action='switch' with artifact_id to work on one"
    }


async def handle_switch(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Switch active artifact context.

    Allows working on a different artifact without losing progress on others.
    """
    artifact_id = arguments.get("artifact_id")

    if not artifact_id:
        # List available artifacts for selection
        artifacts = list_artifacts(state)
        if not artifacts:
            return {
                "status": "NO_ARTIFACTS",
                "message": "No artifacts tracked. Run action='discover' or action='start' first.",
                "next_action": "Call action='discover' to find existing files, or action='start' to create new"
            }

        return {
            "status": "SELECT_ARTIFACT",
            "message": "Specify artifact_id to switch to",
            "available_artifacts": [
                {
                    "artifact_id": a["artifact_id"],
                    "label": a["label"],
                    "type": a["type"],
                    "status": a["status"],
                    "workflow_step": a["workflow_step"]
                }
                for a in artifacts
            ],
            "next_action": "Call eliza_workflow(action='switch', artifact_id='<id>')"
        }

    # Validate artifact exists
    artifact = get_artifact(state, artifact_id)
    if not artifact:
        return {
            "status": "ERROR",
            "message": f"Artifact {artifact_id} not found",
            "next_action": "Call action='list' to see available artifacts"
        }

    # Switch active artifact
    set_active_artifact(workspace_path, artifact_id)

    return {
        "status": "SWITCHED",
        "active_artifact": {
            "artifact_id": artifact_id,
            "label": artifact["label"],
            "type": artifact["type"],
            "workflow_step": artifact["workflow_step"],
            "status": artifact["status"]
        },
        "message": f"Now working on: {artifact['label']}",
        "next_action": f"Call action='continue' to proceed with {artifact['label']}"
    }


def handle_list(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    List all tracked artifacts with their status.
    """
    artifacts = list_artifacts(state)
    active_id = state.get("active_artifact_id")

    artifact_summaries = []
    by_status = {}

    for a in artifacts:
        summary = {
            "artifact_id": a["artifact_id"],
            "label": a["label"],
            "type": a["type"],
            "file_path": a.get("file_path"),
            "status": a["status"],
            "workflow_step": a["workflow_step"],
            "discovered": a.get("discovered", False),
            "is_active": a["artifact_id"] == active_id,
            "retry_count": a["retry_state"]["attempt"]
        }
        artifact_summaries.append(summary)

        # Group by status
        status = a["status"]
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(summary)

    return {
        "status": "LIST",
        "total_artifacts": len(artifacts),
        "active_artifact_id": active_id,
        "artifacts": artifact_summaries,
        "by_status": {k: len(v) for k, v in by_status.items()},
        "credentials_valid": state["credentials"]["jwt_provided"],
        "discovery_completed": state["discovery"]["completed"],
        "message": f"{len(artifacts)} artifacts: {', '.join(f'{k}={len(v)}' for k, v in by_status.items()) or 'none'}"
    }


async def handle_start(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start a new workflow for a NEW artifact.

    V2.0 CHANGE: Does NOT reset entire state anymore.
    - Creates a new artifact entry in the artifacts array
    - Reuses existing credentials if already validated
    - Each artifact has independent workflow state
    """
    requirement = arguments.get("requirement", "")

    if not requirement:
        return {
            "status": "ERROR",
            "message": "Missing 'requirement'. Please specify what you want to build.",
            "next_action": "Call eliza_workflow with action='start' and requirement='your description'"
        }

    # Ensure v2.0 state (don't reset - that was the old behavior)
    if state.get("version") != "2.0":
        state = migrate_v1_to_v2(workspace_path)

    # Detect artifact type from requirement
    artifact_type = detect_artifact_type_from_requirement(requirement)

    # Generate a label from the requirement
    label = generate_label_from_requirement(requirement)

    # Create new artifact (does NOT reset other artifacts or credentials)
    state, artifact_id = add_artifact(
        workspace_path,
        artifact_type=artifact_type,
        label=label,
        discovered=False
    )

    # Set as active artifact
    set_active_artifact(workspace_path, artifact_id)

    # Store requirement in artifact's intent
    update_artifact_intent(workspace_path, artifact_id, user_requirement=requirement)

    # Check if credentials already exist and are valid
    if state["credentials"]["jwt_provided"] and state["credentials"]["env_file_written"]:
        # Skip credential collection, go directly to intent detection
        return {
            "status": "CREDENTIALS_REUSED",
            "current_step": WorkflowStep.DETECT_INTENT.value,
            "artifact_id": artifact_id,
            "artifact_label": label,
            "artifact_type": artifact_type,
            "message": f"Created new artifact '{label}'. Reusing existing credentials.",
            "next_action": "Call action='continue' to proceed with intent detection and function search"
        }
    else:
        # Need credentials - same as before
        return await step_check_credentials(arguments, workspace_path, get_or_create_state(workspace_path))


def detect_artifact_type_from_requirement(requirement: str) -> str:
    """Detect artifact type from user requirement text."""
    req_lower = requirement.lower()

    if any(word in req_lower for word in ["agent", "rag", "chat", "assistant", "bot"]):
        return "agent"
    if any(word in req_lower for word in ["function", "sdk", "python"]):
        return "function"
    # Default to nugget (most common)
    return "nugget"


def generate_label_from_requirement(requirement: str) -> str:
    """Generate a short label from the requirement text."""
    # Take first 50 chars, remove special chars, title case
    label = requirement[:50].strip()
    label = re.sub(r'[^a-zA-Z0-9\s]', '', label)
    label = ' '.join(label.split())  # Normalize whitespace
    return label.title() if label else "New Artifact"


async def handle_continue(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Continue workflow from current step."""
    current_step = get_current_step(state)

    # Determine next step based on current state
    if current_step == WorkflowStep.INIT.value:
        return await step_check_credentials(arguments, workspace_path, state)

    if current_step == WorkflowStep.CHECK_CREDENTIALS.value:
        # Check if credentials were provided
        if not state["credentials"]["jwt_provided"]:
            return await step_check_credentials(arguments, workspace_path, state)
        return await step_write_env_file(arguments, workspace_path, state)

    if current_step == WorkflowStep.REQUEST_CREDENTIALS.value:
        return await step_check_credentials(arguments, workspace_path, state)

    if current_step == WorkflowStep.WRITE_ENV_FILE.value:
        if not state["credentials"]["env_file_written"]:
            return await step_write_env_file(arguments, workspace_path, state)
        return await step_detect_intent(arguments, workspace_path, state)

    if current_step == WorkflowStep.DETECT_INTENT.value:
        return await step_search_functions(arguments, workspace_path, state)

    if current_step == WorkflowStep.SEARCH_FUNCTIONS.value:
        if not is_step_completed(state, WorkflowStep.SEARCH_FUNCTIONS):
            return await step_search_functions(arguments, workspace_path, state)
        return await step_create_artifact(arguments, workspace_path, state)

    if current_step == WorkflowStep.CREATE_ARTIFACT.value:
        return await step_static_validation(arguments, workspace_path, state)

    if current_step == WorkflowStep.STATIC_VALIDATION.value:
        artifact_data = get_artifact_data(state)
        if artifact_data.get("validated"):
            return await step_ready_to_write(arguments, workspace_path, state)
        return await step_static_validation(arguments, workspace_path, state)

    if current_step == WorkflowStep.READY_TO_WRITE.value:
        return await step_ready_to_write(arguments, workspace_path, state)

    if current_step == WorkflowStep.RUNTIME_VALIDATION.value:
        return await step_complete(arguments, workspace_path, state)

    if current_step == WorkflowStep.RETRY_LOOP.value:
        return await handle_retry(arguments, workspace_path, state)

    if current_step == WorkflowStep.COMPLETE.value:
        return {
            "status": WorkflowStatus.COMPLETE.value,
            "message": "Workflow already completed. Call with action='reset' to start a new one.",
            "next_action": "No further action needed"
        }

    # Default: check credentials
    return await step_check_credentials(arguments, workspace_path, state)


# =============================================================================
# WORKFLOW STEPS
# =============================================================================

async def step_check_credentials(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 1: Check if credentials are provided and valid."""
    jwt_token = arguments.get("jwt_token")
    agent_id = arguments.get("agent_id")
    initiative_id = arguments.get("initiative_id")
    env = arguments.get("env", "QA")

    # Check if we have JWT
    if jwt_token:
        valid, error = validate_jwt_format(jwt_token)
        if not valid:
            return {
                "status": WorkflowStatus.NEED_CREDENTIALS.value,
                "current_step": WorkflowStep.CHECK_CREDENTIALS.value,
                "error": error,
                "prompt_for_user": "Please provide a valid JWT token. You can get this from the Eliza portal.",
                "next_action": "Ask user for their JWT token, then call eliza_workflow with jwt_token=<token>"
            }

    # Check if we have agent_id (required for nuggets)
    if agent_id:
        valid, error = validate_agent_id_format(agent_id)
        if not valid:
            return {
                "status": WorkflowStatus.NEED_CREDENTIALS.value,
                "current_step": WorkflowStep.CHECK_CREDENTIALS.value,
                "error": error,
                "prompt_for_user": "Please provide a valid agent ID (UUID format).",
                "next_action": "Ask user for their agent ID, then call eliza_workflow with agent_id=<uuid>"
            }

    # Check initiative_id if provided
    if initiative_id:
        valid, error = validate_initiative_id_format(initiative_id)
        if not valid:
            return {
                "status": WorkflowStatus.NEED_CREDENTIALS.value,
                "current_step": WorkflowStep.CHECK_CREDENTIALS.value,
                "error": error,
                "prompt_for_user": "Please provide a valid initiative ID.",
                "next_action": "Ask user for their initiative ID, then call eliza_workflow with initiative_id=<id>"
            }

    # If we have required credentials, store them
    if jwt_token and agent_id:
        update_credentials(workspace_path, jwt_token, agent_id, initiative_id, env)
        update_step(workspace_path, WorkflowStep.CHECK_CREDENTIALS, "passed")

        # Move to write env file
        return await step_write_env_file(arguments, workspace_path, get_or_create_state(workspace_path))

    # Request credentials
    state = update_step(workspace_path, WorkflowStep.REQUEST_CREDENTIALS)
    missing = []
    if not jwt_token:
        missing.append("jwt_token")
    if not agent_id:
        missing.append("agent_id")

    return {
        "status": WorkflowStatus.NEED_CREDENTIALS.value,
        "current_step": WorkflowStep.REQUEST_CREDENTIALS.value,
        "missing_credentials": missing,
        "prompt_for_user": f"I need your Eliza credentials to proceed. Missing: {', '.join(missing)}",
        "next_action": f"Ask user for: {', '.join(missing)}. Then call eliza_workflow with these values."
    }


async def step_write_env_file(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 2: Write .env file with credentials."""
    creds = state["credentials"]

    if not creds["jwt_provided"]:
        return await step_check_credentials(arguments, workspace_path, state)

    # Generate .env content
    env_content = f"""# Eliza Credentials - Generated by eliza_workflow
# DO NOT COMMIT THIS FILE

ELIZA_JWT_TOKEN={arguments.get('jwt_token', '')}
ELIZA_AGENT_ID={creds['agent_id'] or ''}
ELIZA_INITIATIVE_ID={creds.get('initiative_id', '')}
ELIZA_ENV={creds['env']}
"""

    env_file_path = os.path.join(workspace_path, ".env")

    # Mark step and provide write instruction
    update_step(workspace_path, WorkflowStep.WRITE_ENV_FILE, "passed")
    mark_env_file_written(workspace_path)

    # Move to intent detection
    return await step_detect_intent(arguments, workspace_path, get_or_create_state(workspace_path))


def get_intent_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get intent data, handling both v1.0 and v2.0 state."""
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return artifact.get("intent", {})
        return {}
    return state.get("intent", {})


def get_artifact_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get artifact data, handling both v1.0 and v2.0 state."""
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return artifact.get("artifact_data", {})
        return {}
    return state.get("artifact", {})


def get_pending_write_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get pending write data, handling both v1.0 and v2.0 state."""
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return artifact.get("pending_write", {})
        return {}
    return state.get("pending_write", {})


def get_retry_state_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get retry state data, handling both v1.0 and v2.0 state."""
    if state.get("version") == "2.0":
        active_id = state.get("active_artifact_id")
        if active_id:
            artifact = get_artifact(state, active_id)
            if artifact:
                return artifact.get("retry_state", {})
        return {}
    return state.get("retry_state", {})


async def step_detect_intent(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 3: Detect user intent from requirement."""
    intent_data = get_intent_data(state)
    requirement = intent_data.get("user_requirement") or arguments.get("requirement", "")

    if not requirement:
        return {
            "status": "ERROR",
            "message": "No requirement found. What do you want to build?",
            "next_action": "Call eliza_workflow with action='start' and requirement='description'"
        }

    # Use smart search for intent detection
    search_result = smart_search(requirement)

    # Store intent results
    update_intent(
        workspace_path,
        detected_intent=search_result.get("detected_intent"),
        required_functions=search_result.get("required_functions", []),
        optional_functions=search_result.get("optional_functions", []),
        discovered_functions=search_result.get("all_functions", [])
    )

    update_step(workspace_path, WorkflowStep.DETECT_INTENT, "passed", {
        "intent": search_result.get("detected_intent"),
        "description": search_result.get("intent_description")
    })

    # Continue to search functions step
    return await step_search_functions(arguments, workspace_path, get_or_create_state(workspace_path))


async def step_search_functions(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 4: Search and present ez* functions."""
    intent_data = get_intent_data(state)

    required_funcs = intent_data.get("required_functions", [])
    optional_funcs = intent_data.get("optional_functions", [])
    all_funcs = intent_data.get("discovered_functions", [])

    if not all_funcs:
        # Re-run search
        requirement = intent_data.get("user_requirement", "")
        if requirement:
            search_result = smart_search(requirement)
            required_funcs = search_result.get("required_functions", [])
            optional_funcs = search_result.get("optional_functions", [])
            all_funcs = search_result.get("all_functions", [])

            update_intent(
                workspace_path,
                required_functions=required_funcs,
                optional_functions=optional_funcs,
                discovered_functions=all_funcs
            )

    # Get function signatures for code generation
    signatures = get_function_signatures(all_funcs)

    update_step(workspace_path, WorkflowStep.SEARCH_FUNCTIONS, "passed", {
        "discovered_functions": all_funcs
    })

    # Build instruction for Cascade to generate code
    intent_name = intent_data.get("detected_intent", "unknown")
    requirement = intent_data.get("user_requirement", "")

    return {
        "status": WorkflowStatus.CREATING.value,
        "current_step": WorkflowStep.CREATE_ARTIFACT.value,
        "detected_intent": intent_name,
        "requirement": requirement,
        "required_functions": required_funcs,
        "optional_functions": optional_funcs,
        "discovered_functions": all_funcs,
        "function_signatures": signatures,
        "next_action": f"""Generate nugget code using these functions:

REQUIRED: {required_funcs}
OPTIONAL: {optional_funcs}

RULES:
1. Use IIFE pattern: (function(data) {{ ... }})()
2. Use var instead of let/const
3. Return a string or use JSON.stringify for objects
4. Use the exact function signatures provided

After generating code, call eliza_workflow with:
- action='continue'
- generated_code='<your code>'
- file_path='<where to save>'"""
    }


async def step_create_artifact(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 5: Receive and store generated code."""
    generated_code = arguments.get("generated_code")
    file_path = arguments.get("file_path")

    if not generated_code:
        return {
            "status": "WAITING",
            "current_step": WorkflowStep.CREATE_ARTIFACT.value,
            "message": "Waiting for generated code",
            "next_action": "Call eliza_workflow with action='continue', generated_code='<code>', file_path='<path>'"
        }

    # Determine artifact type from file path
    artifact_type = "nugget"
    if file_path:
        if "agent" in file_path.lower():
            artifact_type = "agent"
        elif "function" in file_path.lower():
            artifact_type = "function"

    # Store the artifact
    update_artifact(workspace_path, artifact_type, generated_code, file_path)
    update_step(workspace_path, WorkflowStep.CREATE_ARTIFACT, "passed")

    # Move to static validation
    return await step_static_validation(arguments, workspace_path, get_or_create_state(workspace_path))


async def step_static_validation(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 6: Run static validation on generated code."""
    artifact = get_artifact_data(state)
    code = artifact.get("code") or arguments.get("generated_code")

    if not code:
        return {
            "status": "ERROR",
            "message": "No code to validate. Generate code first.",
            "next_action": "Call eliza_workflow with generated_code='<your code>'"
        }

    # Run validation
    code_type = "nugget" if artifact.get("type") == "nugget" else None
    validation_result = validate_code(code, code_type)

    if validation_result.valid:
        # Mark validation passed
        update_artifact(workspace_path, validated=True)
        update_step(workspace_path, WorkflowStep.STATIC_VALIDATION, "passed")

        # Prepare for write
        file_path = artifact.get("file_path") or arguments.get("file_path")
        update_pending_write(workspace_path, file_path, code, True)

        return await step_ready_to_write(arguments, workspace_path, get_or_create_state(workspace_path))
    else:
        # Validation failed - extract errors from ValidationResult
        errors = [issue.message for issue in validation_result.issues]
        error_msg = "; ".join(errors) if errors else "Static validation failed"

        # Get fix suggestion from auto-fixed code or individual issue fixes
        fix_suggestion = ""
        if validation_result.fixed_code:
            fix_suggestion = "Auto-fixed code available"
        elif validation_result.issues:
            fixes = [issue.fix for issue in validation_result.issues if issue.fix]
            fix_suggestion = "; ".join(fixes) if fixes else "Review the error and fix the code"

        add_retry_error(workspace_path, error_msg, fix_suggestion)

        update_step(workspace_path, WorkflowStep.STATIC_VALIDATION, "failed", {
            "errors": errors
        })

        state = get_or_create_state(workspace_path)
        retry_state = get_retry_state_data(state)
        if can_retry(state):
            return {
                "status": WorkflowStatus.VALIDATION_FAILED.value,
                "current_step": WorkflowStep.RETRY_LOOP.value,
                "errors": errors,
                "fix_suggestion": fix_suggestion,
                "fixed_code": validation_result.fixed_code,
                "retry_attempt": retry_state.get("attempt", 0),
                "max_attempts": retry_state.get("max_attempts", 3),
                "next_action": f"""VALIDATION FAILED. Fix the code:

ERRORS:
{chr(10).join('- ' + e for e in errors)}

FIX:
{fix_suggestion}

Then call eliza_workflow with:
- action='retry'
- generated_code='<fixed code>'"""
            }
        else:
            return {
                "status": WorkflowStatus.FAILED.value,
                "message": "Maximum retry attempts exceeded",
                "errors": retry_state.get("errors", []),
                "next_action": "Call eliza_workflow with action='reset' to start over"
            }


async def step_ready_to_write(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Step 7: File is ready to be written."""
    pending = get_pending_write_data(state)
    artifact = get_artifact_data(state)

    file_path = pending.get("file_path") or artifact.get("file_path")
    content = pending.get("content") or artifact.get("code")

    if not file_path or not content:
        return {
            "status": "ERROR",
            "message": "Missing file path or content",
            "next_action": "Call eliza_workflow with file_path and generated_code"
        }

    # Update state for hook verification
    update_pending_write(workspace_path, file_path, content, True)
    state = update_step(workspace_path, WorkflowStep.READY_TO_WRITE, "passed")
    save_state(workspace_path, state)

    return {
        "status": WorkflowStatus.READY_TO_WRITE.value,
        "current_step": WorkflowStep.READY_TO_WRITE.value,
        "file_to_write": {
            "path": file_path,
            "content": content
        },
        "message": "Code validated. Ready to write file.",
        "next_action": f"""Write the file to: {file_path}

The post-write hook will automatically run runtime validation.
After writing, call eliza_workflow with action='continue' to complete."""
    }


async def step_complete(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Final step: Workflow complete."""
    update_step(workspace_path, WorkflowStep.COMPLETE, "passed")

    return {
        "status": WorkflowStatus.COMPLETE.value,
        "current_step": WorkflowStep.COMPLETE.value,
        "message": "Workflow completed successfully!",
        "artifact": get_artifact_data(state),
        "next_action": "No further action needed. The nugget/agent is ready to use."
    }


async def handle_retry(arguments: Dict[str, Any], workspace_path: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle retry after validation failure."""
    generated_code = arguments.get("generated_code")

    if not generated_code:
        # Return current error info
        retry_state = get_retry_state_data(state)
        errors = retry_state.get("errors", [])
        latest_error = errors[-1] if errors else {"error": "Unknown error"}

        return {
            "status": WorkflowStatus.RETRY.value,
            "current_step": WorkflowStep.RETRY_LOOP.value,
            "error": latest_error.get("error"),
            "fix_suggestion": latest_error.get("fix_suggestion"),
            "retry_attempt": retry_state.get("attempt", 0),
            "max_attempts": retry_state.get("max_attempts", 3),
            "next_action": "Fix the code based on the error, then call eliza_workflow with action='retry' and generated_code='<fixed code>'"
        }

    # Update artifact with fixed code
    update_artifact(workspace_path, code=generated_code)

    # Re-run validation
    return await step_static_validation(arguments, workspace_path, get_or_create_state(workspace_path))
