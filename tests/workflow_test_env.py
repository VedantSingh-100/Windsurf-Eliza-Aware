#!/usr/bin/env python3
"""
Interactive Testing Environment for Multi-Artifact Workflow

This script creates test environments to verify workflow behavior.
Use it to:
1. Create test workspaces with different scenarios
2. Run workflow actions and see state changes
3. Simulate multiple artifacts
4. Visualize the workflow state

Usage:
    python tests/workflow_test_env.py [scenario]

Scenarios:
    empty       - Empty workspace (fresh start)
    existing    - Workspace with existing nugget files
    v1_migrate  - Workspace with v1.0 state to migrate
    multi       - Workspace with multiple artifacts
    all         - Run all scenarios sequentially

Example:
    python tests/workflow_test_env.py empty
    python tests/workflow_test_env.py all
"""

import asyncio
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from tools.workflow_state import (
    create_empty_state,
    create_empty_state_v2,
    load_state,
    save_state,
    add_artifact,
    get_artifact,
    get_active_artifact,
    set_active_artifact,
    list_artifacts,
    update_artifact_step,
    update_artifact_pending_write,
    migrate_v1_to_v2,
    WorkflowStep,
)
from tools.discovery import discover_artifacts, sync_discovered_to_state
from tools.workflow import handle_eliza_workflow


# =============================================================================
# CONSOLE OUTPUT HELPERS
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_step(text: str):
    """Print a step."""
    print(f"{Colors.CYAN}>>> {text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}[ERROR] {text}{Colors.ENDC}")


def print_state(state: Dict[str, Any], title: str = "Current State"):
    """Print workflow state in readable format."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{title}:{Colors.ENDC}")
    print(f"  Version: {state.get('version', 'unknown')}")

    # Credentials
    creds = state.get('credentials', {})
    print(f"  Credentials:")
    print(f"    JWT Provided: {creds.get('jwt_provided', False)}")
    print(f"    Agent ID: {creds.get('agent_id', 'None')[:20] + '...' if creds.get('agent_id') else 'None'}")
    print(f"    Env File Written: {creds.get('env_file_written', False)}")

    # Artifacts (v2.0)
    if 'artifacts' in state:
        artifacts = state.get('artifacts', [])
        print(f"  Artifacts: {len(artifacts)}")
        for i, art in enumerate(artifacts):
            active = " (ACTIVE)" if art.get('artifact_id') == state.get('active_artifact_id') else ""
            print(f"    [{i+1}] {art.get('label', 'unknown')}{active}")
            print(f"        Type: {art.get('type')}, Step: {art.get('workflow_step')}")
            print(f"        Status: {art.get('status')}, Discovered: {art.get('discovered')}")
            print(f"        Retries: {art.get('retry_state', {}).get('attempt', 0)}/3")
    else:
        # v1.0 format
        print(f"  Current Step: {state.get('current_step')}")
        artifact = state.get('artifact', {})
        print(f"  Artifact Type: {artifact.get('type')}")

    print()


def print_result(result: Dict[str, Any], action: str):
    """Print workflow action result."""
    status = result.get('status', 'unknown')
    color = Colors.GREEN if status not in ['ERROR', 'FAILED'] else Colors.RED

    print(f"\n{color}Action '{action}' Result:{Colors.ENDC}")
    print(f"  Status: {status}")

    if 'message' in result:
        print(f"  Message: {result['message'][:100]}...")
    if 'discovered_count' in result:
        print(f"  Discovered: {result['discovered_count']} files")
    if 'artifacts' in result:
        print(f"  Artifacts: {len(result['artifacts'])}")
    if 'active_artifact_id' in result:
        print(f"  Active: {result['active_artifact_id'][:8]}...")

    print()


# =============================================================================
# TEST WORKSPACE SETUP
# =============================================================================

def create_test_workspace(scenario: str) -> str:
    """
    Create a test workspace for a specific scenario.

    Args:
        scenario: One of 'empty', 'existing', 'v1_migrate', 'multi'

    Returns:
        Path to the test workspace
    """
    workspace = tempfile.mkdtemp(prefix=f"workflow_test_{scenario}_")

    if scenario == 'empty':
        # Just create the directory, nothing else
        pass

    elif scenario == 'existing':
        # Create existing nugget files
        nuggets_dir = os.path.join(workspace, "nuggets")
        os.makedirs(nuggets_dir)

        # Email nugget
        with open(os.path.join(nuggets_dir, "email.nugget.js"), 'w') as f:
            f.write('''/**
 * Eliza Nugget: Email Sender
 * Agent ID: test-agent-12345
 * Description: Sends emails via ezMail
 */
(function(data) {
    var result = ezMail(data.to, "Subject", data.body);
    return JSON.stringify(result);
})()''')

        # Search nugget
        with open(os.path.join(nuggets_dir, "search.nugget.js"), 'w') as f:
            f.write('''/**
 * Eliza Nugget: Web Search
 * Description: Searches the internet
 */
(function(data) {
    return ezInternetSearch(data.query);
})()''')

        # Log nugget
        with open(os.path.join(nuggets_dir, "logger.nugget.js"), 'w') as f:
            f.write('(function(data) { return ezLog(data); })()')

    elif scenario == 'v1_migrate':
        # Create v1.0 state with progress
        state = create_empty_state(workspace)
        state["credentials"]["jwt_provided"] = True
        state["credentials"]["agent_id"] = "v1-agent-12345678-1234-1234-1234-123456789abc"
        state["credentials"]["env_file_written"] = True
        state["artifact"]["type"] = "nugget"
        state["artifact"]["code"] = "(function(data) { ezLog('hello'); })()"
        state["artifact"]["file_path"] = os.path.join(workspace, "nuggets", "v1_nugget.js")
        state["intent"]["user_requirement"] = "Log messages for debugging"
        state["current_step"] = WorkflowStep.READY_TO_WRITE.value
        state["steps_completed"] = [
            {"step": WorkflowStep.CHECK_CREDENTIALS.value, "status": "passed"},
            {"step": WorkflowStep.WRITE_ENV_FILE.value, "status": "passed"},
            {"step": WorkflowStep.SEARCH_FUNCTIONS.value, "status": "passed"},
            {"step": WorkflowStep.CREATE_ARTIFACT.value, "status": "passed"},
            {"step": WorkflowStep.STATIC_VALIDATION.value, "status": "passed"},
        ]
        state["pending_write"]["file_path"] = state["artifact"]["file_path"]
        state["pending_write"]["content"] = state["artifact"]["code"]
        state["pending_write"]["validated"] = True
        save_state(workspace, state)

    elif scenario == 'multi':
        # Create v2 state with multiple artifacts
        state = create_empty_state_v2(workspace)
        state["credentials"]["jwt_provided"] = True
        state["credentials"]["agent_id"] = "multi-agent-12345678-1234-1234-1234-123456789abc"
        state["credentials"]["env_file_written"] = True
        save_state(workspace, state)

        # Add multiple artifacts
        state, id1 = add_artifact(workspace, "nugget", "Email Sender",
                                   os.path.join(workspace, "nuggets/email.nugget.js"))
        state, id2 = add_artifact(workspace, "nugget", "Web Search",
                                   os.path.join(workspace, "nuggets/search.nugget.js"))
        state, id3 = add_artifact(workspace, "agent", "Newsletter Agent",
                                   os.path.join(workspace, "agents/newsletter.py"))

        # Progress first artifact to COMPLETE
        update_artifact_step(workspace, id1, WorkflowStep.COMPLETE)
        update_artifact_pending_write(workspace, id1, validated=True)

        # Progress second artifact to STATIC_VALIDATION
        update_artifact_step(workspace, id2, WorkflowStep.STATIC_VALIDATION)

        # Leave third at INIT

        # Set second as active
        set_active_artifact(workspace, id2)

    return workspace


# =============================================================================
# SCENARIO RUNNERS
# =============================================================================

async def run_empty_scenario():
    """Run empty workspace scenario."""
    print_header("SCENARIO: Empty Workspace (Fresh Start)")

    workspace = create_test_workspace('empty')
    print_success(f"Created workspace: {workspace}")

    try:
        # Step 1: Check status
        print_step("Step 1: Check initial status")
        result = await handle_eliza_workflow({
            "action": "status",
            "workspace_path": workspace
        })
        print_result(result, "status")

        # Step 2: Try to start without credentials
        print_step("Step 2: Start without credentials")
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send newsletter emails",
            "workspace_path": workspace
        })
        print_result(result, "start")

        if result.get("status") == "NEED_CREDENTIALS":
            print_success("Correctly requested credentials")

        # Step 3: Start with credentials
        print_step("Step 3: Start with valid credentials")
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send newsletter emails",
            "jwt_token": valid_jwt,
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "workspace_path": workspace
        })
        print_result(result, "start")

        # Show final state
        state = load_state(workspace)
        print_state(state, "Final State")

        # Verify v2.0
        if state.get("version") == "2.0":
            print_success("State is v2.0")
        else:
            print_error(f"Expected v2.0, got {state.get('version')}")

        if len(state.get("artifacts", [])) == 1:
            print_success("One artifact created")
        else:
            print_error(f"Expected 1 artifact, got {len(state.get('artifacts', []))}")

    finally:
        print_step("Cleaning up workspace")
        shutil.rmtree(workspace, ignore_errors=True)
        print_success("Done!")


async def run_existing_scenario():
    """Run existing files scenario."""
    print_header("SCENARIO: Existing Files (Midway Start)")

    workspace = create_test_workspace('existing')
    print_success(f"Created workspace with existing files: {workspace}")

    try:
        # List existing files
        nuggets_dir = os.path.join(workspace, "nuggets")
        files = os.listdir(nuggets_dir)
        print_step(f"Existing files: {files}")

        # Step 1: Discovery
        print_step("Step 1: Discover existing files")

        # Need to create state first
        state = create_empty_state_v2(workspace)
        save_state(workspace, state)

        result = await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace
        })
        print_result(result, "discover")

        if result.get("discovered_count", 0) > 0:
            print_success(f"Discovered {result['discovered_count']} files")

        # Step 2: List discovered artifacts
        print_step("Step 2: List discovered artifacts")
        result = await handle_eliza_workflow({
            "action": "list",
            "workspace_path": workspace
        })
        print_result(result, "list")

        # Show state
        state = load_state(workspace)
        print_state(state, "State After Discovery")

        # Verify all files discovered
        for artifact in state.get("artifacts", []):
            if artifact.get("discovered"):
                print_success(f"Artifact '{artifact.get('label')}' marked as discovered")
            else:
                print_warning(f"Artifact '{artifact.get('label')}' not marked as discovered")

    finally:
        print_step("Cleaning up workspace")
        shutil.rmtree(workspace, ignore_errors=True)
        print_success("Done!")


async def run_v1_migrate_scenario():
    """Run v1 to v2 migration scenario."""
    print_header("SCENARIO: V1 to V2 Migration")

    workspace = create_test_workspace('v1_migrate')
    print_success(f"Created workspace with v1 state: {workspace}")

    try:
        # Show original v1 state
        state = load_state(workspace)
        print_step("Original v1 state:")
        print(f"  Version: {state.get('version')}")
        print(f"  Current Step: {state.get('current_step')}")
        print(f"  Credentials Saved: {state.get('credentials', {}).get('jwt_provided')}")

        # Step 1: Check status (should auto-detect v1)
        print_step("Step 1: Check status")
        result = await handle_eliza_workflow({
            "action": "status",
            "workspace_path": workspace
        })
        print_result(result, "status")

        # Step 2: Migrate explicitly
        print_step("Step 2: Migrate to v2")
        new_state = migrate_v1_to_v2(workspace)
        print_state(new_state, "State After Migration")

        # Verify migration
        if new_state.get("version") == "2.0":
            print_success("Successfully migrated to v2.0")
        else:
            print_error("Migration failed!")

        if new_state.get("_v1_backup"):
            print_success("V1 backup preserved")

        if len(new_state.get("artifacts", [])) > 0:
            artifact = new_state["artifacts"][0]
            print_success(f"Artifact migrated: {artifact.get('label')}")
            print(f"    Step preserved: {artifact.get('workflow_step')}")

    finally:
        print_step("Cleaning up workspace")
        shutil.rmtree(workspace, ignore_errors=True)
        print_success("Done!")


async def run_multi_scenario():
    """Run multi-artifact scenario."""
    print_header("SCENARIO: Multiple Artifacts")

    workspace = create_test_workspace('multi')
    print_success(f"Created workspace with multiple artifacts: {workspace}")

    try:
        # Show initial state
        state = load_state(workspace)
        print_state(state, "Initial State")

        # Step 1: List all artifacts
        print_step("Step 1: List all artifacts")
        result = await handle_eliza_workflow({
            "action": "list",
            "workspace_path": workspace
        })
        print_result(result, "list")

        # Step 2: Check each artifact's status
        print_step("Step 2: Individual artifact status")
        for artifact in state.get("artifacts", []):
            status = artifact.get("status")
            step = artifact.get("workflow_step")
            retries = artifact.get("retry_state", {}).get("attempt", 0)
            print(f"  {artifact.get('label')}: status={status}, step={step}, retries={retries}")

        # Step 3: Switch to a different artifact
        print_step("Step 3: Switch active artifact")
        artifacts = state.get("artifacts", [])
        if len(artifacts) > 1:
            # Switch to first artifact (Email Sender - should be COMPLETE)
            target_id = artifacts[0]["artifact_id"]
            result = await handle_eliza_workflow({
                "action": "switch",
                "artifact_id": target_id,
                "workspace_path": workspace
            })
            print_result(result, "switch")

            state = load_state(workspace)
            active = get_active_artifact(state)
            if active and active["artifact_id"] == target_id:
                print_success(f"Switched to: {active.get('label')}")

        # Step 4: Add new artifact (should reuse credentials)
        print_step("Step 4: Add new artifact (credentials should be reused)")
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Create a new chat bot",
            "workspace_path": workspace
        })
        print_result(result, "start")

        # Should NOT ask for credentials
        if result.get("status") == "NEED_CREDENTIALS":
            print_error("Should have reused credentials!")
        else:
            print_success("Credentials were reused!")

        # Final state
        state = load_state(workspace)
        print_state(state, "Final State")

        print_success(f"Total artifacts: {len(state.get('artifacts', []))}")

    finally:
        print_step("Cleaning up workspace")
        shutil.rmtree(workspace, ignore_errors=True)
        print_success("Done!")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point."""
    scenarios = {
        'empty': run_empty_scenario,
        'existing': run_existing_scenario,
        'v1_migrate': run_v1_migrate_scenario,
        'multi': run_multi_scenario,
    }

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable scenarios:")
        for name in scenarios:
            print(f"  - {name}")
        print("  - all")
        sys.exit(1)

    scenario = sys.argv[1].lower()

    if scenario == 'all':
        for name, runner in scenarios.items():
            await runner()
            print("\n" + "="*60 + "\n")
    elif scenario in scenarios:
        await scenarios[scenario]()
    else:
        print_error(f"Unknown scenario: {scenario}")
        print(f"Available: {', '.join(scenarios.keys())}, all")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
