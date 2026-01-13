#!/usr/bin/env python3
"""
Cascade Hook: Validate Nuggets After Write

This hook runs automatically after Cascade writes code.
It validates nugget files in TWO stages:
1. STATIC VALIDATION - Checks syntax, structure, ez* function usage
2. RUNTIME VALIDATION - Calls Eliza API to actually execute the nugget

WORKFLOW INTEGRATION (Jan 2026):
- Updates .eliza/workflow_state.json after validation
- Formats retry errors with fix suggestions for Cascade
- Tracks retry attempts (max 3)

Triggered by: post_write_code hook in .windsurf/hooks.json

Credentials are loaded from (in priority order):
1. Environment variables: ELIZA_JWT_TOKEN, ELIZA_AGENT_ID, ELIZA_ENV
2. .env file in the workspace root (auto-detected from file path)
"""

import json
import os
import re
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from validation.static import validate_code, Severity

# Try to import workflow state tools
try:
    from tools.workflow_state import (
        get_or_create_state,
        update_step,
        add_retry_error,
        can_retry,
        WorkflowStep,
        save_state,
        # V2.0 multi-artifact functions
        get_artifact_by_path,
        get_active_artifact,
        update_artifact_step,
        update_artifact_retry,
        can_artifact_retry,
    )
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False


def load_env_file(file_path: str) -> dict:
    """
    Load environment variables from a .env file.

    Args:
        file_path: Path to .env file

    Returns:
        Dict of key-value pairs from the .env file
    """
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars

    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                            (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    env_vars[key] = value
    except Exception:
        pass

    return env_vars


def find_workspace_root(file_path: str) -> str:
    """
    Find the workspace root by looking for .git, .env, or package.json.

    Args:
        file_path: Path to a file in the workspace

    Returns:
        Path to workspace root, or directory containing the file
    """
    current = os.path.dirname(os.path.abspath(file_path))

    # Walk up looking for workspace markers
    for _ in range(10):  # Max 10 levels up
        if os.path.exists(os.path.join(current, '.git')) or \
                os.path.exists(os.path.join(current, '.env')) or \
                os.path.exists(os.path.join(current, 'package.json')):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # Hit root
            break
        current = parent

    return os.path.dirname(os.path.abspath(file_path))


def update_workflow_after_validation(workspace: str, passed: bool, errors: list[str] = None, fix_suggestion: str = "", file_path: str = None) -> dict:
    """
    Update workflow state after validation completes.

    V2.0: Updates specific artifact identified by file_path.

    Args:
        workspace: Path to workspace directory
        passed: Whether validation passed
        errors: List of error messages (if failed)
        fix_suggestion: Suggested fix for the error
        file_path: Path to the file being validated (for v2.0 artifact lookup)

    Returns:
        Updated state dict (or empty dict if workflow not available)
    """
    if not WORKFLOW_AVAILABLE:
        return {}

    state = get_or_create_state(workspace)

    # V2.0 multi-artifact workflow
    if state.get("version") == "2.0":
        # Look up artifact by file path
        artifact = None
        if file_path:
            artifact = get_artifact_by_path(state, file_path)
        if artifact is None:
            artifact = get_active_artifact(state)

        if artifact is None:
            # No artifact found - fall back to legacy behavior
            return _update_workflow_v1(workspace, passed, errors, fix_suggestion)

        artifact_id = artifact["artifact_id"]

        if passed:
            # Mark runtime validation as passed for this artifact
            update_artifact_step(workspace, artifact_id, WorkflowStep.RUNTIME_VALIDATION, "passed")
            # Mark artifact as complete
            update_artifact_step(workspace, artifact_id, WorkflowStep.COMPLETE, "passed")
            # Update artifact status
            state = get_or_create_state(workspace)
            artifact = get_artifact_by_path(state, file_path) or get_active_artifact(state)
            if artifact:
                artifact["status"] = "deployed"
                save_state(workspace, state)
        else:
            # Mark runtime validation as failed for this artifact
            update_artifact_step(workspace, artifact_id, WorkflowStep.RUNTIME_VALIDATION, "failed", {"errors": errors})

            # Add to artifact's retry state
            error_msg = "; ".join(errors) if errors else "Validation failed"
            update_artifact_retry(workspace, artifact_id, error_msg, fix_suggestion)

            # Update artifact's current step to retry loop
            state = get_or_create_state(workspace)
            artifact = get_artifact_by_path(state, file_path) or get_active_artifact(state)
            if artifact:
                artifact["workflow_step"] = WorkflowStep.RETRY_LOOP.value
                save_state(workspace, state)

        return get_or_create_state(workspace)
    else:
        # V1.0 single-artifact workflow
        return _update_workflow_v1(workspace, passed, errors, fix_suggestion)


def _update_workflow_v1(workspace: str, passed: bool, errors: list[str] = None, fix_suggestion: str = "") -> dict:
    """V1.0 legacy workflow update logic."""
    state = get_or_create_state(workspace)

    if passed:
        # Mark runtime validation as passed
        update_step(workspace, WorkflowStep.RUNTIME_VALIDATION, "passed")
        # Mark workflow as complete
        update_step(workspace, WorkflowStep.COMPLETE, "passed")
    else:
        # Mark runtime validation as failed
        update_step(workspace, WorkflowStep.RUNTIME_VALIDATION, "failed", {"errors": errors})

        # Add to retry state
        error_msg = "; ".join(errors) if errors else "Validation failed"
        add_retry_error(workspace, error_msg, fix_suggestion)

        # Update current step to retry loop
        state = get_or_create_state(workspace)
        state["current_step"] = WorkflowStep.RETRY_LOOP.value
        save_state(workspace, state)

    return get_or_create_state(workspace)


def format_retry_error(workspace: str, errors: list[str], fix_suggestion: str = "", file_path: str = None) -> str:
    """
    Format error for Cascade with retry information.

    V2.0: Uses per-artifact retry state.

    This creates a structured error message that Cascade can parse
    and use to call eliza_workflow(action='retry').
    """
    if not WORKFLOW_AVAILABLE:
        return "\n".join(errors)

    state = get_or_create_state(workspace)

    # V2.0: Get retry state from specific artifact
    if state.get("version") == "2.0":
        artifact = None
        if file_path:
            artifact = get_artifact_by_path(state, file_path)
        if artifact is None:
            artifact = get_active_artifact(state)

        if artifact:
            retry_state = artifact.get("retry_state", {})
            attempt = retry_state.get("attempt", 0)
            max_attempts = retry_state.get("max_attempts", 3)
            can_retry_flag = can_artifact_retry(artifact)
            artifact_label = artifact.get("label", "Unknown")
        else:
            retry_state = state.get("retry_state", {})
            attempt = retry_state.get("attempt", 0)
            max_attempts = retry_state.get("max_attempts", 3)
            can_retry_flag = can_retry(state)
            artifact_label = None
    else:
        retry_state = state.get("retry_state", {})
        attempt = retry_state.get("attempt", 0)
        max_attempts = retry_state.get("max_attempts", 3)
        can_retry_flag = can_retry(state)
        artifact_label = None

    output = []
    if artifact_label:
        output.append(f"RUNTIME_VALIDATION_FAILED [{artifact_label}] (Attempt {attempt}/{max_attempts})")
    else:
        output.append(f"RUNTIME_VALIDATION_FAILED (Attempt {attempt}/{max_attempts})")
    output.append("")
    output.append("ERRORS:")
    for err in errors:
        output.append(f"  - {err}")
    output.append("")

    if fix_suggestion:
        output.append("FIX:")
        output.append(f"  {fix_suggestion}")
        output.append("")

    if can_retry_flag:
        output.append("NEXT: Call eliza_workflow(action='retry') to get fixed code")
    else:
        output.append("MAX_RETRIES_EXCEEDED: Call eliza_workflow(action='reset') to start over")

    return "\n".join(output)


def get_credentials(file_path: str = None) -> tuple[str, str, str]:
    """
    Get Eliza credentials from environment or .env file.

    Priority:
    1. Environment variables
    2. .env file in workspace root
    3. .env file in Eliza-Aware repo (fallback)

    Returns:
        (jwt_token, agent_id, env)
    """
    # Start with environment variables
    jwt_token = os.environ.get("ELIZA_JWT_TOKEN")
    agent_id = os.environ.get("ELIZA_AGENT_ID")
    env = os.environ.get("ELIZA_ENV", "QA")

    # If file_path provided, try to load from .env in workspace
    if file_path:
        workspace_root = find_workspace_root(file_path)
        env_file = os.path.join(workspace_root, '.env')

        if os.path.exists(env_file):
            env_vars = load_env_file(env_file)

            # Only override if not already set from environment
            if not jwt_token and 'ELIZA_JWT_TOKEN' in env_vars:
                jwt_token = env_vars['ELIZA_JWT_TOKEN']
            if not agent_id and 'ELIZA_AGENT_ID' in env_vars:
                agent_id = env_vars['ELIZA_AGENT_ID']
            if 'ELIZA_ENV' in env_vars:
                env = env_vars['ELIZA_ENV']

    # Fallback: Try Eliza-Aware repo .env (where this hook lives)
    if not jwt_token or not agent_id:
        hook_dir = os.path.dirname(os.path.abspath(__file__))
        eliza_aware_env = os.path.join(hook_dir, '..', '..', '.env')
        if os.path.exists(eliza_aware_env):
            env_vars = load_env_file(eliza_aware_env)
            if not jwt_token and 'ELIZA_JWT_TOKEN' in env_vars:
                jwt_token = env_vars['ELIZA_JWT_TOKEN']
            if not agent_id and 'ELIZA_AGENT_ID' in env_vars:
                agent_id = env_vars['ELIZA_AGENT_ID']
            if 'ELIZA_ENV' in env_vars:
                env = env_vars['ELIZA_ENV']

    return jwt_token, agent_id, env


# CogEngine base URLs by environment
COGENGINE_URLS = {
    "DEV": "https://cognitive-engine-personal.dev.bny.net/cog",
    "TEST": "https://cognitive-engine-personal.test.bny.net/cog",
    "QA": "https://cognitive-engine-personal.qa.bny.net/cog",
    "PROD": "https://cognitive-engine-personal.bny.net/cog"
}

# Pattern to match nugget files
NUGGET_PATTERNS = [
    r".*nuggets?/.*\.(js|ts)$",      # files in nugget(s) directory
    r".*nugget.*\.(js|ts)$",          # files with nugget in name
    r".*\.nugget\.(js|ts)$",          # files with .nugget. extension (MCP generated)
    r".*nuggets/[a-f0-9-]+/.*\.js$",  # MCP generated: nuggets/{agent_id}/file.js
]

# Python SDK patterns that are hallucinated (non-existent)
PYTHON_SDK_ERRORS = [
    (r"eliza\.Agent\.from_id\(", "eliza.Agent.from_id() doesn't exist", "Use: Agent(env='QA', agent_id='...')"),
    (r"eliza\.Agent\.load\(", "eliza.Agent.load() doesn't exist", "Use: Agent(env='QA', agent_id='...')"),
    (r"eliza\.Agent\(", "eliza.Agent() doesn't exist", "Use: from bnym_eliza.genai.agent import Agent"),
    (r"agent\.load\(", "agent.load() doesn't exist", "Agent auto-loads when agent_id provided"),
    (r"Agent\.create\(", "Agent.create() is wrong", "Use: agent = Agent(...); agent.create()"),
    (r"agent\.query\(", "agent.query() doesn't exist", "Use: agent.chat(query='...')"),
    (r"agent\.search\(", "agent.search() doesn't exist", "Use: agent.search_documents(content=[...])"),
]

# Patterns that indicate incorrect add_function() usage
# These check for common mistakes in function definitions
ADD_FUNCTION_SCHEMA_ERRORS = []


def check_nugget_function_schema(content: str) -> list[str]:
    """
    Check if code defines a function with functionType=NUGGET but missing nuggetId.
    This is a common error - NUGGET type requires an existing nugget reference.

    IMPORTANT: Nuggets CANNOT exist without an agent. The correct workflow is:
    1. Create agent first (via create_function_agent MCP tool or SDK)
    2. Create nugget on that agent (via create_nugget MCP tool)
    3. Then reference the nuggetId in functionType="NUGGET"
    """
    errors = []

    # Find all dicts with functionType: "NUGGET"
    if '"functionType"' in content and '"NUGGET"' in content:
        # Check if nuggetId is present
        if '"nuggetId"' not in content and "'nuggetId'" not in content:
            errors.append(
                '❌ functionType="NUGGET" requires nuggetId - but you cannot create nuggets inline!\n'
                '⚠ NUGGETS REQUIRE AN AGENT FIRST. You cannot create a nugget without an agent.\n'
                '\n'
                '→ REQUIRED WORKFLOW:\n'
                '  1. STOP writing Python code manually\n'
                '  2. Use the `create_function_agent` MCP tool to create an agent (requires JWT token)\n'
                '  3. Use the `create_nugget` MCP tool to create the nugget on that agent\n'
                '  4. The MCP tool will return the nuggetId - use that in your code\n'
                '\n'
                '→ WHY: Nuggets are JavaScript code that run on Eliza servers. They use ez* functions\n'
                '       (ezInternetSearch, ezChatCompletions, etc.) which ONLY work in nuggets, not Python.\n'
                '\n'
                '→ DO NOT use PYTHON_STATIC or REST as workarounds - they cannot do what nuggets do.'
            )

    return errors


def is_nugget_file(path: str) -> bool:
    """Check if a file path matches nugget patterns."""
    for pattern in NUGGET_PATTERNS:
        if re.match(pattern, path, re.IGNORECASE):
            return True
    return False


def is_eliza_python_file(path: str) -> bool:
    """Check if a Python file uses Eliza SDK."""
    if not path.endswith('.py'):
        return False
    # Exclude hook scripts (they contain the patterns as strings)
    if '/scripts/hooks/' in path or 'validate_' in path:
        return False
    try:
        with open(path, 'r') as f:
            content = f.read()
        return 'eliza' in content.lower() or 'bnym_eliza' in content
    except:
        return False


def validate_python_sdk(path: str) -> tuple[bool, list[str]]:
    """
    Validate Python file for common Eliza SDK hallucinations.

    Returns:
        (passed, list of error messages)
    """
    try:
        with open(path, 'r') as f:
            content = f.read()
    except:
        return True, []

    errors = []

    # Check for hallucinated SDK patterns
    for pattern, error_msg, fix in PYTHON_SDK_ERRORS:
        if re.search(pattern, content):
            errors.append(f"❌ {error_msg}\n    → FIX: {fix}")

    # Check for NUGGET function schema errors
    errors.extend(check_nugget_function_schema(content))

    return len(errors) == 0, errors


def static_validate(code: str) -> tuple[bool, str, str | None]:
    """
    Stage 1: Static validation.

    Returns:
        (passed, message, fixed_code or None)
    """
    result = validate_code(code, "nugget")

    if result.valid:
        return True, "✅ Static validation PASSED", None

    errors = [i for i in result.issues if i.severity == Severity.ERROR]
    error_msgs = [f"  - {e.message}" + (f" → Fix: {e.fix}" if e.fix else "") for e in errors]

    return False, "❌ Static validation FAILED:\n" + "\n".join(error_msgs), result.fixed_code


def is_network_error(error: Exception) -> bool:
    """Check if an exception is a network/proxy error (not a validation failure)."""
    error_str = str(error).lower()
    network_indicators = [
        'proxy', 'proxyerror', 'connectionerror', 'timeout',
        'tunnel', '407', 'authenticationrequired', 'max retries',
        'connection refused', 'name or service not known'
    ]
    return any(indicator in error_str for indicator in network_indicators)


def runtime_validate(code: str, jwt_token: str, agent_id: str, env: str = "QA") -> tuple[bool, str]:
    """
    Stage 2: Runtime validation via Eliza API.

    Creates a temporary nugget, executes it, then cleans up.

    NOTE: Network/proxy errors are treated as WARNINGS, not failures.
    This is because MCP tools already do runtime validation before returning.
    The hook's runtime validation is defense-in-depth, not the primary gate.

    Returns:
        (passed, message)
    """
    base_url = COGENGINE_URLS.get(env, COGENGINE_URLS["QA"])
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
        "x-jwt-assertion": jwt_token,
        "REQUESTER-ID": "VALIDATION_HOOK"
    }

    # Step 1: Create temporary nugget
    create_url = f"{base_url}/agents/{agent_id}/nuggets/"
    create_payload = {
        "agentId": agent_id,
        "agentDocId": "none",
        "agentNuggetId": "",
        "label": "_validation_temp_nugget",
        "description": "Temporary nugget for validation - will be deleted",
        "status": "active",
        "call": {"@type": "code", "language": "JavaScript", "code": code},
        "params": {},
        "controlFlags": {},
        "metadata": {"_validation_temp": True}
    }

    try:
        create_resp = requests.post(create_url, json=create_payload, headers=headers, verify=False, timeout=30)
        if create_resp.status_code != 200:
            return False, f"❌ Runtime validation FAILED - Could not create temp nugget: {create_resp.text[:200]}"

        nugget_id = create_resp.json().get("agentNuggetId")
        if not nugget_id:
            return False, "❌ Runtime validation FAILED - No nugget ID returned"
    except Exception as e:
        # Network/proxy errors should NOT block - MCP already validated
        if is_network_error(e):
            return True, f"⚠ Runtime validation SKIPPED - Network error (proxy/connection): {str(e)[:100]}... (Static validation passed, which is sufficient)"
        return False, f"❌ Runtime validation FAILED - API error: {str(e)}"

    # Step 2: Execute the nugget
    call_url = f"{base_url}/agents/{agent_id}/nuggets/{nugget_id}/call"
    test_data = {"data": {"query": "validation_test", "_validation": True}}

    try:
        exec_resp = requests.post(call_url, json=test_data, headers=headers, verify=False, timeout=60)

        if exec_resp.status_code == 200:
            exec_passed = True
            exec_message = "✅ Runtime validation PASSED - Nugget executed successfully"
        else:
            exec_passed = False
            exec_message = f"❌ Runtime validation FAILED - Execution error: {exec_resp.text[:300]}"
    except Exception as e:
        # Network/proxy errors should NOT block - MCP already validated
        if is_network_error(e):
            exec_passed = True
            exec_message = f"⚠ Runtime validation SKIPPED - Network error: {str(e)[:100]}..."
        else:
            exec_passed = False
            exec_message = f"❌ Runtime validation FAILED - Execution error: {str(e)}"

    # Step 3: Cleanup - delete the temporary nugget
    delete_url = f"{base_url}/agents/{agent_id}/nuggets/{nugget_id}"
    try:
        requests.delete(delete_url, headers=headers, verify=False, timeout=10)
    except:
        pass  # Best effort cleanup

    return exec_passed, exec_message


def validate_nugget_file(path: str, jwt_token: str = None, agent_id: str = None, env: str = "QA") -> tuple[bool, str, bool]:
    """
    Full validation pipeline for a nugget file.

    Returns:
        (passed, message, credentials_missing)
    """
    try:
        with open(path, 'r') as f:
            code = f.read()
    except Exception as e:
        return False, f"Could not read file: {e}", False

    messages = [f"\n🔍 Validating: {path}"]
    all_passed = True
    credentials_missing = False

    # Stage 1: Static validation (always runs)
    static_passed, static_msg, fixed_code = static_validate(code)
    messages.append(f"  {static_msg}")

    if not static_passed:
        all_passed = False
        if fixed_code:
            messages.append(f"  🔧 Auto-fix available - {len(fixed_code)} chars")

    # Stage 2: Runtime validation (OPTIONAL - MCP tools already validate)
    # Network/credential issues are warnings, not failures, since MCP did validation
    if jwt_token and agent_id:
        if static_passed:
            runtime_passed, runtime_msg = runtime_validate(code, jwt_token, agent_id, env)
            messages.append(f"  {runtime_msg}")
            # Runtime failures due to network are already handled as warnings in runtime_validate
            if not runtime_passed:
                all_passed = False
        else:
            messages.append("  ⬛ Runtime validation SKIPPED - Fix static errors first")
    else:
        # No credentials - this is OK if static validation passed
        # MCP tools do runtime validation before returning, so hook runtime is redundant
        credentials_missing = True
        if static_passed:
            messages.append("  ⚠ Runtime validation SKIPPED - No credentials (static passed, which is sufficient)")
        else:
            all_passed = False
            messages.append("  ⚠ Runtime validation SKIPPED - No credentials found")

    return all_passed, "\n".join(messages), credentials_missing


def main():
    """
    Main hook entry point.

    Reads hook payload from stdin, checks if any nugget files were modified,
    and validates them through both static and runtime stages.

    Credentials are loaded from:
    1. Environment variables (ELIZA_JWT_TOKEN, ELIZA_AGENT_ID, ELIZA_ENV)
    2. .env file in the workspace root
    """
    # Read hook payload from stdin
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    # Extract file paths (deduplicated)
    tool_info = payload.get("tool_info", {})
    file_path = tool_info.get("file_path", "")
    changed_files = list(set(payload.get("changed_files", []) + ([file_path] if file_path else [])))

    # Filter to nugget files and Python Eliza files
    nugget_files = [f for f in changed_files if is_nugget_file(f)]
    python_files = [f for f in changed_files if is_eliza_python_file(f)]

    # Exit early only if no relevant files
    if not nugget_files and not python_files:
        return 0

    # Get credentials - use first file to find workspace root
    first_file = nugget_files[0] if nugget_files else (python_files[0] if python_files else file_path)
    jwt_token, agent_id, env = get_credentials(first_file)

    print("🔮 Nugget Validation Hook")
    print("=" * 50)

    # Show credential source info
    if jwt_token:
        print(f"  🔑 JWT: Found ({'env' if os.environ.get('ELIZA_JWT_TOKEN') else '.env file'})")
    if agent_id:
        print(f"  🤖 Agent ID: {agent_id[:8]}... ({'env' if os.environ.get('ELIZA_AGENT_ID') else '.env file'})")
    print(f"  🌍 Environment: {env}")
    print("")

    # Get workspace root for workflow state
    workspace = find_workspace_root(first_file) if first_file else os.getcwd()

    # Validate each nugget file
    all_passed = True
    any_credentials_missing = False
    all_errors = []

    for nf in nugget_files:
        if os.path.exists(nf):
            passed, message, creds_missing = validate_nugget_file(nf, jwt_token, agent_id, env)
            print(message)
            if not passed:
                all_passed = False
                # Extract errors from message for workflow state
                for line in message.split('\n'):
                    if '❌' in line or 'FAILED' in line:
                        all_errors.append(line.strip())
            if creds_missing:
                any_credentials_missing = True

    # Also validate Python files that use Eliza
    for pf in python_files:
        print(f"\n🔍 Validating Python SDK usage: {pf}")
        py_passed, py_errors = validate_python_sdk(pf)
        if not py_passed:
            all_passed = False
            for err in py_errors:
                print(f"  {err}")
        else:
            print("  ✅ Python SDK patterns OK")

    print("=" * 50)

    # ===== UPDATE WORKFLOW STATE (Jan 2026) =====
    # Build fix suggestion for workflow state
    fix_suggestion = ""
    if not all_passed:
        fix_suggestion = "Review the errors above and fix the code."
        if any_credentials_missing:
            fix_suggestion = "Provide credentials first, then retry."

    # Only update workflow state if workspace exists and is writable
    # V2.0: Update per-artifact state for each nugget file
    if WORKFLOW_AVAILABLE and nugget_files and os.path.isdir(workspace):
        try:
            for nf in nugget_files:
                if all_passed:
                    update_workflow_after_validation(workspace, True, file_path=nf)
                    print(f"📋 Workflow state updated: COMPLETE ({os.path.basename(nf)})")
                else:
                    update_workflow_after_validation(workspace, False, all_errors, fix_suggestion, file_path=nf)
                    print(f"📋 Workflow state updated: RETRY_LOOP ({os.path.basename(nf)})")
        except (PermissionError, OSError) as e:
            print(f"📋 Workflow state update skipped: {e}")

    if not all_passed:
        # Collect all errors for stderr (compact format for Cascade)
        stderr_errors = []

        if any_credentials_missing:
            for nf in nugget_files:
                workspace = find_workspace_root(nf)
                stderr_errors.append(
                    f"STOP. CREDENTIALS REQUIRED. "
                    f"You MUST ask user: 'Please provide your Eliza JWT token and agent ID for validation.' "
                    f"Then create file {workspace}/.env with ELIZA_JWT_TOKEN=<token> ELIZA_AGENT_ID=<agent_id> ELIZA_ENV=QA. "
                    f"Then re-save {os.path.basename(nf)} to validate."
                )

        # Collect Python SDK errors
        for pf in python_files:
            _, py_errors = validate_python_sdk(pf)
            for err in py_errors:
                # Special handling for NUGGET errors - give clear MCP tool directive
                if 'functionType="NUGGET"' in err or 'nuggetId' in err:
                    stderr_errors.append(
                        f"STOP. NUGGET_WORKFLOW_ERROR file={os.path.basename(pf)} "
                        f"You are trying to use functionType=NUGGET without a nuggetId. "
                        f"NUGGETS CANNOT EXIST WITHOUT AN AGENT. "
                        f"REQUIRED: Use the `create_function_agent` MCP tool FIRST to create an agent (ask user for JWT token), "
                        f"THEN use the `create_nugget` MCP tool to create the nugget on that agent. "
                        f"The MCP tool will return the nuggetId. "
                        f"DO NOT write Python code manually. DO NOT use PYTHON_STATIC or REST as workarounds."
                    )
                else:
                    # Standard error formatting
                    clean_err = err.replace("❌ ", "").replace("\n", "    → FIX: ", " fix=")
                    stderr_errors.append(f"VALIDATION_FAILED file={os.path.basename(pf)} {clean_err}")

        # Collect nugget static validation errors
        for nf in nugget_files:
            if os.path.exists(nf):
                with open(nf, 'r') as f:
                    code = f.read()
                static_passed, static_msg, _ = static_validate(code)
                if not static_passed:
                    # Extract error from static_msg
                    stderr_errors.append(f"VALIDATION_FAILED file={os.path.basename(nf)} {static_msg.replace(chr(10), ' ')}")

        # ===== WORKFLOW-AWARE ERROR FORMATTING (Jan 2026) =====
        # V2.0: Format retry error with per-artifact info
        if WORKFLOW_AVAILABLE and nugget_files:
            # Use workflow-formatted retry error (use first nugget file for artifact lookup)
            retry_error = format_retry_error(workspace, all_errors, fix_suggestion, file_path=nugget_files[0])
            sys.stderr.write(retry_error + "\n\n")

        # Write compact errors to stderr (this is what Cascade sees with exit code 2)
        for err in stderr_errors:
            sys.stderr.write(err + "\n")

        # Human-readable summary to stdout
        print("\n❌ VALIDATION FAILED - See errors above")
        if WORKFLOW_AVAILABLE:
            print("💡 TIP: Call eliza_workflow(action='retry') to get fixed code")

        # Exit code 2 = Blocking Error that Cascade sees
        return 2

    print("✅ All validations passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())