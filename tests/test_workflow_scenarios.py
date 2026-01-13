"""
Scenario-Based Integration Tests for Multi-Artifact Workflow

Tests real-world developer scenarios:
1. Empty repo - starting fresh
2. Existing files - midway start with discovery
3. Multiple nuggets - creating several in one session
4. Switching context - working on different artifacts
5. Credential reuse - not asking for credentials repeatedly
6. Migration - upgrading from v1 to v2

These tests verify the DETERMINISTIC behavior of the workflow system.
"""

import pytest
import asyncio
import os
import sys
import json
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.workflow_state import (
    create_empty_state,
    create_empty_state_v2,
    get_or_create_state,
    save_state,
    load_state,
    update_credentials,
    update_step,
    mark_env_file_written,
    add_artifact,
    get_artifact,
    get_artifact_by_path,
    get_active_artifact,
    set_active_artifact,
    list_artifacts,
    update_artifact_step,
    update_artifact_pending_write,
    update_artifact_retry,
    migrate_v1_to_v2,
    WorkflowStep,
)
from tools.discovery import (
    discover_artifacts,
    sync_discovered_to_state,
)
from tools.workflow import handle_eliza_workflow


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def empty_workspace():
    """Create an empty workspace (fresh start scenario)."""
    workspace = tempfile.mkdtemp(prefix="scenario_empty_")
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def workspace_with_existing_nuggets():
    """Create workspace with pre-existing nugget files (midway start)."""
    workspace = tempfile.mkdtemp(prefix="scenario_existing_")

    # Create nuggets directory with files
    nuggets_dir = os.path.join(workspace, "nuggets")
    os.makedirs(nuggets_dir)

    # Existing nugget 1
    with open(os.path.join(nuggets_dir, "email.nugget.js"), 'w') as f:
        f.write('''/**
 * Eliza Nugget: Email Sender
 * Agent ID: existing-agent-id-12345
 */
(function(data) {
    var result = ezMail(data.to, "Subject", data.body);
    return JSON.stringify(result);
})()''')

    # Existing nugget 2
    with open(os.path.join(nuggets_dir, "search.nugget.js"), 'w') as f:
        f.write('''(function(data) {
    return ezInternetSearch(data.query);
})()''')

    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def workspace_with_v1_state():
    """Create workspace with v1.0 state (migration scenario)."""
    workspace = tempfile.mkdtemp(prefix="scenario_v1_")

    # Create v1 state with some progress
    state = create_empty_state(workspace)
    state["credentials"]["jwt_provided"] = True
    state["credentials"]["agent_id"] = "v1-agent-id-12345"
    state["credentials"]["env_file_written"] = True
    state["artifact"]["type"] = "nugget"
    state["artifact"]["code"] = "(function(data) { return ezLog(data); })()"
    state["artifact"]["file_path"] = "/old/path/nugget.js"
    state["intent"]["user_requirement"] = "Log debug messages"
    state["current_step"] = WorkflowStep.READY_TO_WRITE.value
    state["steps_completed"].append({
        "step": WorkflowStep.CHECK_CREDENTIALS.value,
        "status": "passed"
    })
    save_state(workspace, state)

    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def valid_jwt():
    """Valid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"


@pytest.fixture
def valid_agent_id():
    """Valid agent ID for testing."""
    return "12345678-1234-1234-1234-123456789abc"


# =============================================================================
# SCENARIO 1: EMPTY REPO (FRESH START)
# =============================================================================

class TestScenarioEmptyRepo:
    """
    Scenario: Developer starts with empty repo, no existing files.

    Expected behavior:
    1. action='status' shows no state
    2. action='start' creates v2.0 state with first artifact
    3. Credentials are requested
    4. After credentials, workflow progresses normally
    """

    @pytest.mark.asyncio
    async def test_empty_repo_status(self, empty_workspace):
        """Status on empty repo shows v2.0 state."""
        result = await handle_eliza_workflow({
            "action": "status",
            "workspace_path": empty_workspace
        })

        assert result["status"] == "STATUS"
        # V2.0 returns artifact count and version
        assert result.get("version") == "2.0" or result.get("artifacts_count") is not None or "current_step" in result

    @pytest.mark.asyncio
    async def test_empty_repo_start_needs_credentials(self, empty_workspace):
        """Starting fresh requires credentials."""
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send newsletter emails",
            "workspace_path": empty_workspace
        })

        assert result["status"] == "NEED_CREDENTIALS"
        assert "jwt" in str(result).lower() or "credentials" in str(result).lower()

    @pytest.mark.asyncio
    async def test_empty_repo_creates_v2_state(self, empty_workspace, valid_jwt, valid_agent_id):
        """Starting fresh creates v2.0 state."""
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send newsletter emails",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        # State should be v2.0
        state = load_state(empty_workspace)
        assert state["version"] == "2.0"

        # Should have one artifact
        assert len(state["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_empty_repo_discover_finds_nothing(self, empty_workspace):
        """Discovery on empty repo finds nothing."""
        # Create state first
        state = create_empty_state_v2(empty_workspace)
        save_state(empty_workspace, state)

        result = await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": empty_workspace
        })

        # API returns total_found, not discovered_count
        assert result.get("total_found", 0) == 0 or result.get("newly_added", 0) == 0


# =============================================================================
# SCENARIO 2: EXISTING FILES (MIDWAY START)
# =============================================================================

class TestScenarioExistingFiles:
    """
    Scenario: Developer has existing nugget files, starts using workflow midway.

    Expected behavior:
    1. action='discover' finds existing files
    2. Files are registered in state as "discovered=True"
    3. Developer can work on discovered files
    4. Credentials are still required once
    """

    @pytest.mark.asyncio
    async def test_discover_finds_existing_files(self, workspace_with_existing_nuggets):
        """Discovery finds existing nugget files."""
        # Create initial state
        state = create_empty_state_v2(workspace_with_existing_nuggets)
        save_state(workspace_with_existing_nuggets, state)

        result = await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace_with_existing_nuggets
        })

        assert result["discovered_count"] == 2
        assert result["status"] == "DISCOVERY_COMPLETE"

    @pytest.mark.asyncio
    async def test_discovered_files_tracked_in_state(self, workspace_with_existing_nuggets):
        """Discovered files are registered in state."""
        state = create_empty_state_v2(workspace_with_existing_nuggets)
        save_state(workspace_with_existing_nuggets, state)

        await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace_with_existing_nuggets
        })

        state = load_state(workspace_with_existing_nuggets)
        assert len(state["artifacts"]) == 2

        for artifact in state["artifacts"]:
            assert artifact["discovered"] is True
            assert artifact["type"] == "nugget"

    @pytest.mark.asyncio
    async def test_discovered_files_lookup_by_path(self, workspace_with_existing_nuggets):
        """Discovered files can be looked up by path."""
        state = create_empty_state_v2(workspace_with_existing_nuggets)
        save_state(workspace_with_existing_nuggets, state)

        await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace_with_existing_nuggets
        })

        state = load_state(workspace_with_existing_nuggets)

        email_path = os.path.join(
            workspace_with_existing_nuggets, "nuggets", "email.nugget.js"
        )
        artifact = get_artifact_by_path(state, email_path)

        assert artifact is not None
        assert "Email" in artifact["label"]

    @pytest.mark.asyncio
    async def test_midway_still_needs_credentials(self, workspace_with_existing_nuggets):
        """Even with discovery, credentials are required once."""
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Create new logging nugget",
            "workspace_path": workspace_with_existing_nuggets
        })

        assert result["status"] == "NEED_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_list_after_discovery(self, workspace_with_existing_nuggets):
        """List shows all discovered artifacts."""
        state = create_empty_state_v2(workspace_with_existing_nuggets)
        save_state(workspace_with_existing_nuggets, state)

        await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace_with_existing_nuggets
        })

        result = await handle_eliza_workflow({
            "action": "list",
            "workspace_path": workspace_with_existing_nuggets
        })

        assert result["status"] == "LIST"
        assert len(result["artifacts"]) == 2


# =============================================================================
# SCENARIO 3: MULTIPLE NUGGETS
# =============================================================================

class TestScenarioMultipleNuggets:
    """
    Scenario: Developer creates multiple nuggets in one session.

    Expected behavior:
    1. First nugget: Requires credentials
    2. Second nugget: Reuses credentials (no re-prompt)
    3. Each nugget has independent workflow state
    4. Each nugget has independent retry counter
    """

    @pytest.mark.asyncio
    async def test_second_nugget_reuses_credentials(self, empty_workspace, valid_jwt, valid_agent_id):
        """Second nugget reuses credentials from first."""
        # Create first nugget
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send newsletter emails",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        # Verify credentials saved
        state = load_state(empty_workspace)
        assert state["credentials"]["jwt_provided"] is True

        # Create second nugget (should NOT need credentials)
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Search the internet",
            "workspace_path": empty_workspace
        })

        # Should NOT ask for credentials again
        assert result["status"] != "NEED_CREDENTIALS"

        # Should have two artifacts
        state = load_state(empty_workspace)
        assert len(state["artifacts"]) == 2

    @pytest.mark.asyncio
    async def test_nuggets_have_independent_state(self, empty_workspace, valid_jwt, valid_agent_id):
        """Each nugget has independent workflow state."""
        # Create first nugget
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send emails",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        first_id = state["active_artifact_id"]

        # Progress first nugget
        update_artifact_step(empty_workspace, first_id, WorkflowStep.COMPLETE)

        # Create second nugget
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Search web",
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        second_id = state["active_artifact_id"]

        # Verify states are independent
        first = get_artifact(state, first_id)
        second = get_artifact(state, second_id)

        assert first["workflow_step"] == WorkflowStep.COMPLETE.value
        assert second["workflow_step"] != WorkflowStep.COMPLETE.value

    @pytest.mark.asyncio
    async def test_nuggets_have_independent_retry(self, empty_workspace, valid_jwt, valid_agent_id):
        """Each nugget has independent retry counter."""
        # Create two nuggets
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Nugget 1",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        first_id = state["active_artifact_id"]

        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Nugget 2",
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        second_id = state["active_artifact_id"]

        # Add errors to first nugget only
        update_artifact_retry(empty_workspace, first_id, "Error 1")
        update_artifact_retry(empty_workspace, first_id, "Error 2")

        # Verify retry states are independent
        state = load_state(empty_workspace)
        first = get_artifact(state, first_id)
        second = get_artifact(state, second_id)

        assert first["retry_state"]["attempt"] == 2
        assert second["retry_state"]["attempt"] == 0


# =============================================================================
# SCENARIO 4: SWITCHING CONTEXT
# =============================================================================

class TestScenarioSwitchingContext:
    """
    Scenario: Developer switches between working on different artifacts.

    Expected behavior:
    1. action='switch' changes active artifact
    2. action='continue' works on active artifact
    3. State is preserved when switching away
    """

    @pytest.mark.asyncio
    async def test_switch_artifact(self, empty_workspace, valid_jwt, valid_agent_id):
        """Can switch between artifacts."""
        # Create two nuggets
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "First nugget",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        first_id = state["active_artifact_id"]

        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Second nugget",
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        second_id = state["active_artifact_id"]

        # Should be on second
        assert get_active_artifact(state)["artifact_id"] == second_id

        # Switch to first
        result = await handle_eliza_workflow({
            "action": "switch",
            "artifact_id": first_id,
            "workspace_path": empty_workspace
        })

        assert result["status"] == "SWITCHED"

        state = load_state(empty_workspace)
        assert get_active_artifact(state)["artifact_id"] == first_id

    @pytest.mark.asyncio
    async def test_state_preserved_on_switch(self, empty_workspace, valid_jwt, valid_agent_id):
        """State is preserved when switching artifacts."""
        # Create nugget and progress it
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "First",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)
        first_id = state["active_artifact_id"]

        # Update first artifact's state
        update_artifact_pending_write(
            empty_workspace, first_id,
            file_path="/path/first.js",
            content="first content",
            validated=True
        )

        # Create and switch to second
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Second",
            "workspace_path": empty_workspace
        })

        # Switch back to first
        await handle_eliza_workflow({
            "action": "switch",
            "artifact_id": first_id,
            "workspace_path": empty_workspace
        })

        # Verify first's state is preserved
        state = load_state(empty_workspace)
        first = get_artifact(state, first_id)
        assert first["pending_write"]["content"] == "first content"
        assert first["pending_write"]["validated"] is True


# =============================================================================
# SCENARIO 5: CREDENTIAL REUSE
# =============================================================================

class TestScenarioCredentialReuse:
    """
    Scenario: Credentials should be asked once and reused.

    Expected behavior:
    1. First artifact: Credentials required
    2. All subsequent artifacts: Credentials reused
    3. After discovery: Credentials still required once
    4. Credentials shared across all artifacts
    """

    @pytest.mark.asyncio
    async def test_credentials_asked_once(self, empty_workspace, valid_jwt, valid_agent_id):
        """Credentials are only asked once."""
        # First start - needs credentials
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "First",
            "workspace_path": empty_workspace
        })
        assert result["status"] == "NEED_CREDENTIALS"

        # Provide credentials
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "First",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        # Second start - should NOT need credentials
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Second",
            "workspace_path": empty_workspace
        })
        assert result["status"] != "NEED_CREDENTIALS"

        # Third start - still no credentials needed
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Third",
            "workspace_path": empty_workspace
        })
        assert result["status"] != "NEED_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_credentials_at_state_level(self, empty_workspace, valid_jwt, valid_agent_id):
        """Credentials are stored at state level, not per-artifact."""
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Test",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        state = load_state(empty_workspace)

        # Credentials should be in state.credentials
        assert state["credentials"]["jwt_provided"] is True
        assert state["credentials"]["agent_id"] == valid_agent_id

        # Artifacts should NOT have their own credentials
        for artifact in state["artifacts"]:
            assert "credentials" not in artifact or artifact.get("credentials") is None


# =============================================================================
# SCENARIO 6: V1 TO V2 MIGRATION
# =============================================================================

class TestScenarioMigration:
    """
    Scenario: Existing v1.0 state needs to migrate to v2.0.

    Expected behavior:
    1. Existing credentials preserved
    2. Existing artifact becomes first entry in artifacts array
    3. Workflow step preserved
    4. Original state backed up
    """

    def test_migration_preserves_credentials(self, workspace_with_v1_state):
        """Migration preserves credentials."""
        v2_state = migrate_v1_to_v2(workspace_with_v1_state)

        assert v2_state["credentials"]["jwt_provided"] is True
        assert v2_state["credentials"]["agent_id"] == "v1-agent-id-12345"
        assert v2_state["credentials"]["env_file_written"] is True

    def test_migration_creates_artifact(self, workspace_with_v1_state):
        """Migration creates artifact from v1 data."""
        v2_state = migrate_v1_to_v2(workspace_with_v1_state)

        assert len(v2_state["artifacts"]) == 1

        artifact = v2_state["artifacts"][0]
        assert artifact["type"] == "nugget"
        assert artifact["artifact_data"]["code"] is not None
        assert artifact["intent"]["user_requirement"] == "Log debug messages"

    def test_migration_preserves_step(self, workspace_with_v1_state):
        """Migration preserves workflow step."""
        v2_state = migrate_v1_to_v2(workspace_with_v1_state)

        artifact = v2_state["artifacts"][0]
        assert artifact["workflow_step"] == WorkflowStep.READY_TO_WRITE.value

    def test_migration_backs_up_v1(self, workspace_with_v1_state):
        """Migration backs up original v1 state."""
        v2_state = migrate_v1_to_v2(workspace_with_v1_state)

        assert "_v1_backup" in v2_state
        assert v2_state["_v1_backup"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_auto_migration_on_start(self, workspace_with_v1_state):
        """Starting workflow auto-migrates v1 state."""
        # Verify v1 state exists
        v1_state = load_state(workspace_with_v1_state)
        assert v1_state["version"] == "1.0"

        # Start new workflow (should trigger migration)
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "New requirement",
            "workspace_path": workspace_with_v1_state
        })

        # State should now be v2
        v2_state = load_state(workspace_with_v1_state)
        assert v2_state["version"] == "2.0"

        # Should have migrated artifact + new one (or just reused credentials)
        # The exact count depends on whether NEED_CREDENTIALS was returned
        assert len(v2_state["artifacts"]) >= 1


# =============================================================================
# DETERMINISM TESTS
# =============================================================================

class TestDeterminism:
    """
    Test that the workflow system is deterministic.

    Same inputs should always produce same outputs.
    """

    @pytest.mark.asyncio
    async def test_same_inputs_same_state(self, empty_workspace, valid_jwt, valid_agent_id):
        """Same inputs produce same state structure."""
        # Run workflow
        await handle_eliza_workflow({
            "action": "start",
            "requirement": "Test requirement",
            "jwt_token": valid_jwt,
            "agent_id": valid_agent_id,
            "workspace_path": empty_workspace
        })

        state1 = load_state(empty_workspace)

        # Create fresh workspace
        workspace2 = tempfile.mkdtemp(prefix="determinism_")
        try:
            await handle_eliza_workflow({
                "action": "start",
                "requirement": "Test requirement",
                "jwt_token": valid_jwt,
                "agent_id": valid_agent_id,
                "workspace_path": workspace2
            })

            state2 = load_state(workspace2)

            # Compare structure (excluding timestamps and UUIDs)
            assert state1["version"] == state2["version"]
            assert len(state1["artifacts"]) == len(state2["artifacts"])
            assert state1["credentials"]["jwt_provided"] == state2["credentials"]["jwt_provided"]
            assert state1["credentials"]["agent_id"] == state2["credentials"]["agent_id"]
        finally:
            shutil.rmtree(workspace2, ignore_errors=True)

    def test_migration_idempotent(self, workspace_with_v1_state):
        """Running migration multiple times produces same result."""
        # First migration
        v2_state_1 = migrate_v1_to_v2(workspace_with_v1_state)
        artifact_count_1 = len(v2_state_1["artifacts"])

        # Second migration (should be no-op)
        v2_state_2 = migrate_v1_to_v2(workspace_with_v1_state)
        artifact_count_2 = len(v2_state_2["artifacts"])

        assert artifact_count_1 == artifact_count_2
        assert v2_state_2["version"] == "2.0"

    @pytest.mark.asyncio
    async def test_discovery_idempotent(self, workspace_with_existing_nuggets):
        """Running discovery multiple times is idempotent."""
        state = create_empty_state_v2(workspace_with_existing_nuggets)
        save_state(workspace_with_existing_nuggets, state)

        # First discovery
        await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace_with_existing_nuggets
        })

        state1 = load_state(workspace_with_existing_nuggets)
        count1 = len(state1["artifacts"])

        # Second discovery
        await handle_eliza_workflow({
            "action": "discover",
            "workspace_path": workspace_with_existing_nuggets
        })

        state2 = load_state(workspace_with_existing_nuggets)
        count2 = len(state2["artifacts"])

        assert count1 == count2
