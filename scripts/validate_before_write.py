#!/usr/bin/env python3
"""
Cascade Hook: Validate BEFORE Write (pre_write_code)

This hook runs BEFORE Cascade writes code. Exit code 2 BLOCKS the write.
This is the only way to truly prevent invalid code from being written.

WORKFLOW ENFORCEMENT (Jan 2026):
- Checks .eliza/workflow_state.json for workflow compliance
- Blocks writes if mandatory steps not completed
- Ensures deterministic Eliza development workflow

Triggered by: pre_write_code hook in .windsurf/hooks.json
"""

import json
import os
import re
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, '..', 'mcp_server'))

from eliza_mcp.validation.static import validate_code

# Try to import workflow state checker
try:
    from tools.workflow_state import (
        load_state,
        get_missing_steps,
        is_step_completed,
        WorkflowStep,
        # V2.0 multi-artifact functions
        get_artifact_by_path,
        get_active_artifact,
        # Credentials-only state detection (Jan 2026)
        is_credentials_only_state,
    )
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False


# Pattern to match nugget files
NUGGET_PATTERNS = [
    r".*nuggets?/.*\.(js|ts)$",
    r".*nugget.*\.(js|ts)$",
    r".*\.nugget\.(js|ts)$",
    r".*nuggets/[a-f0-9-]+/.*\.js$",
]

# Python SDK patterns that are hallucinated
PYTHON_SDK_ERRORS = [
    (r"eliza\.Agent\.from_id\(", "eliza.Agent.from_id() doesn't exist", "Agent(env='QA', agent_id='...')"),
    (r"eliza\.Agent\.load\(", "eliza.Agent.load() doesn't exist", "Agent(env='QA', agent_id='...')"),
    (r"eliza\.Agent\(", "eliza.Agent() doesn't exist", "from bnym_eliza.genai.agent import Agent"),
    (r"agent\.load\(", "agent.load() doesn't exist", "Agent auto-loads when agent_id provided"),
    (r"Agent\.create\(", "Agent.create() is wrong", "agent = Agent(...); agent.create()"),
    (r"agent\.query\(", "agent.query() doesn't exist", "agent.chat(query='...')"),
    (r"agent\.search\(", "agent.search() doesn't exist", "agent.search_documents(content=[...])"),
]

# add_function() schema errors (placeholder - use function-based check instead)
ADD_FUNCTION_ERRORS = {}


def check_nugget_function_schema(content: str) -> list[str]:
    """Check if code defines a function with functionType=NUGGET but missing nuggetId."""
    errors = []
    if '"functionType"' in content and '"NUGGET"' in content:
        if '"nuggetId"' not in content and "'nuggetId'" not in content:
            errors.append(
                'functionType="NUGGET" requires nuggetId - create nugget via API first, '
                'OR use functionType="PYTHON_STATIC" for inline code'
            )
    return errors


def is_nugget_file(path: str) -> bool:
    for pattern in NUGGET_PATTERNS:
        if re.match(pattern, path, re.IGNORECASE):
            return True
    return False


def is_eliza_python_file(path: str, content: str) -> bool:
    if not path.endswith('.py'):
        return False
    if 'validate_' in path and '_write.py' in path:
        return False  # Exclude hook scripts
    return 'eliza' in content.lower() or 'bnym_eliza' in content


def validate_python_content(content: str) -> list[str]:
    """Check Python content for SDK hallucinations."""
    errors = []
    for pattern, error_msg, fix in PYTHON_SDK_ERRORS:
        if re.search(pattern, content):
            errors.append(f"{error_msg} fix={fix}")
    # Check NUGGET function schema errors
    errors.extend(check_nugget_function_schema(content))
    return errors


def reconstruct_file_content(file_path: str, edits: list) -> str:
    """
    Reconstruct what the file will look like after edits.

    For pre_write_code, we get 'edits' not the final file.
    We need to apply edits to get the would-be content.
    """
    # Try to read existing file
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except:
        content = ""

    # Apply edits (simplified - assumes edits are replacements or full content)
    for edit in edits:
        if 'new_string' in edit:
            if 'old_string' in edit and edit['old_string']:
                content = content.replace(edit['old_string'], edit['new_string'])
            else:
                # Full file write
                content = edit['new_string']
        elif 'content' in edit:
            content = edit['content']

    return content


def find_workspace_root(file_path: str) -> str:
    current = os.path.dirname(os.path.abspath(file_path))
    for _ in range(10):
        if os.path.exists(os.path.join(current, '.git')) or \
                os.path.exists(os.path.join(current, '.env')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.dirname(os.path.abspath(file_path))


def load_env_file(env_path: str) -> dict:
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    env_vars[key.strip()] = value.strip().strip('"\'')
    except:
        pass
    return env_vars


def check_workflow_state(workspace: str, file_path: str) -> list[str]:
    """
    Check if workflow state allows writing this file.

    V2.0: Supports multi-artifact workflows. Looks up artifact by file path.

    Returns list of errors if workflow is incomplete.
    """
    if not WORKFLOW_AVAILABLE:
        return []  # Skip check if workflow module not available

    errors = []

    # Load workflow state
    state = load_state(workspace)

    if state is None:
        errors.append(
            "WORKFLOW_REQUIRED: No workflow state found. "
            "Use the eliza_workflow tool before writing Eliza code. "
            "Call: eliza_workflow(action='start', requirement='your description')"
        )
        return errors

    # Check for CREDENTIALS_ONLY state (lazy init - not suitable for CREATE operations)
    if is_credentials_only_state(state):
        errors.append(
            "CREDENTIALS_ONLY: State was created via lazy initialization (for read/execute operations). "
            "Creating artifacts requires the full workflow. "
            "Call: eliza_workflow(action='start', requirement='your description', workspace_path='...')"
        )
        return errors

    # Check shared credentials (same for v1 and v2)
    if not state.get("credentials", {}).get("env_file_written"):
        errors.append(
            "CREDENTIALS_NOT_SAVED: The .env file has not been written. "
            "Complete the credential collection step in the workflow."
        )

    # V2.0 multi-artifact workflow
    if state.get("version") == "2.0":
        # Look up artifact by file path
        artifact = get_artifact_by_path(state, file_path)

        if artifact is None:
            # Try active artifact as fallback
            artifact = get_active_artifact(state)

        if artifact is None:
            errors.append(
                f"UNTRACKED_FILE: '{file_path}' is not tracked in workflow state. "
                "Call eliza_workflow(action='discover') to register existing files, "
                "or eliza_workflow(action='start', requirement='...') for new files."
            )
            return errors

        # Check artifact's pending write
        pending = artifact.get("pending_write", {})
        if not pending.get("validated"):
            errors.append(
                f"NOT_VALIDATED: Artifact '{artifact.get('label')}' has not been validated. "
                "Call eliza_workflow(action='continue') to run validation first."
            )

        # Check artifact's workflow step
        workflow_step = artifact.get("workflow_step", "INIT")
        if workflow_step not in ["READY_TO_WRITE", "RUNTIME_VALIDATION", "COMPLETE"]:
            errors.append(
                f"WORKFLOW_INCOMPLETE: Artifact '{artifact.get('label')}' is at step '{workflow_step}'. "
                "Must reach READY_TO_WRITE step before writing. "
                "Call eliza_workflow(action='continue')."
            )

    else:
        # V1.0 single-artifact workflow (legacy behavior)
        missing = get_missing_steps(state)
        if missing:
            errors.append(
                f"WORKFLOW_INCOMPLETE: Missing steps: {', '.join(missing)}. "
                "Continue the workflow with eliza_workflow(action='continue')."
            )

        # Check if this file matches the pending write
        pending = state.get("pending_write", {})
        expected_path = pending.get("file_path")
        if expected_path:
            # Normalize paths for comparison
            norm_expected = os.path.normpath(expected_path)
            norm_actual = os.path.normpath(file_path)
            if norm_expected != norm_actual and not norm_actual.endswith(os.path.basename(norm_expected)):
                errors.append(
                    f"UNEXPECTED_FILE: Workflow expects to write '{expected_path}', "
                    f"but attempting to write '{file_path}'. "
                    "Use eliza_workflow to update the target file."
                )

        # Check if pending write is validated
        if not pending.get("validated"):
            errors.append(
                "NOT_VALIDATED: The code has not been validated. "
                "Call eliza_workflow(action='continue') to run validation first."
            )

    return errors


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_info = payload.get("tool_info", {})
    file_path = tool_info.get("file_path", "")
    edits = tool_info.get("edits", [])

    if not file_path:
        return 0

    # Reconstruct content from edits
    content = reconstruct_file_content(file_path, edits)

    errors = []

    # Find workspace root first
    workspace = find_workspace_root(file_path)

    # Check if nugget file
    if is_nugget_file(file_path):
        # ===== WORKFLOW STATE CHECK (Jan 2026) =====
        # This is the PRIMARY enforcement mechanism for deterministic workflow
        workflow_errors = check_workflow_state(workspace, file_path)
        if workflow_errors:
            # Workflow errors take precedence - block immediately
            for err in workflow_errors:
                errors.append(err)
            # Don't do other checks if workflow is incomplete
            # (they'll just add noise)

        # Static validation (only if workflow passed or not available)
        if not workflow_errors or not WORKFLOW_AVAILABLE:
            result = validate_code(content, "nugget")
            if not result.valid:
                for issue in result.issues:
                    errors.append(f"NUGGET_ERROR: {issue.message}" + (f" fix={issue.fix}" if issue.fix else ""))

        # Check for credentials (required for runtime validation later)
        env_path = os.path.join(workspace, '.env')
        env_vars = load_env_file(env_path)

        if 'ELIZA_JWT_TOKEN' not in env_vars or 'ELIZA_AGENT_ID' not in env_vars:
            errors.append(
                f"CREDENTIALS_REQUIRED: Before writing nugget files, you MUST ask user for JWT token and agent ID. "
                f"Create {env_path} with ELIZA_JWT_TOKEN=<token> ELIZA_AGENT_ID=<agent_id> ELIZA_ENV=QA first."
            )

    # Check if Eliza Python file
    elif is_eliza_python_file(file_path, content):
        py_errors = validate_python_content(content)
        for err in py_errors:
            errors.append(f"PYTHON_SDK_ERROR: {err}")

    if errors:
        # Write to stderr (Cascade sees this with exit code 2)
        sys.stderr.write(f"BLOCKED: Cannot write {os.path.basename(file_path)}\n")
        for err in errors:
            sys.stderr.write(f"  {err}\n")
        return 2  # Blocking error - prevents the write

    return 0


if __name__ == "__main__":
    sys.exit(main())