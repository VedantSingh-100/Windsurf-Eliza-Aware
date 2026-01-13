"""
Tests for V2.0 Multi-Artifact Workflow State Management

Tests all v2.0 functionality:
- Multi-artifact state schema
- Artifact CRUD operations
- Per-artifact workflow tracking
- V1 to V2 migration
- Artifact-by-path lookup (critical for hooks)
- Shared credentials handling
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
    # V1 functions (for migration testing)
    create_empty_state,
    get_or_create_state,
    update_step,
    update_credentials,
    update_pending_write,
    add_retry_error,
    save_state,
    load_state,
    WorkflowStep,
    WorkflowStatus,
    MANDATORY_STEPS,
    # V2 functions
    create_empty_state_v2,
    create_artifact_state,
    add_artifact,
    get_artifact,
    get_artifact_by_path,
    get_artifact_by_label,
    get_active_artifact,
    set_active_artifact,
    list_artifacts,
    remove_artifact,
    update_artifact_step,
    update_artifact_intent,
    update_artifact_code,
    update_artifact_pending_write,
    update_artifact_retry,
    can_artifact_retry,
    reset_artifact_retry,
    migrate_v1_to_v2,
    get_legacy_artifact,
    validate_state_for_write_v2,
)


# =============================================================================
# V2.0 STATE SCHEMA TESTS
# =============================================================================

class TestV2StateSchema:
    """Test v2.0 state structure and creation."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_v2_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_create_empty_state_v2(self, temp_workspace):
        """Test creating a new empty v2.0 state."""
        state = create_empty_state_v2(temp_workspace)

        assert state["version"] == "2.0"
        assert "session_id" in state
        assert "credentials" in state
        assert "artifacts" in state
        assert isinstance(state["artifacts"], list)
        assert len(state["artifacts"]) == 0
        assert state["active_artifact_id"] is None
        assert "discovery" in state
        assert state["discovery"]["completed"] is False

    def test_create_artifact_state(self):
        """Test creating artifact state entry."""
        artifact = create_artifact_state(
            artifact_type="nugget",
            label="test_nugget",
            file_path="/path/to/test.nugget.js",
            discovered=False
        )

        assert "artifact_id" in artifact
        assert artifact["type"] == "nugget"
        assert artifact["label"] == "test_nugget"
        assert artifact["file_path"] == "/path/to/test.nugget.js"
        assert artifact["discovered"] is False
        assert artifact["workflow_step"] == WorkflowStep.INIT.value
        assert artifact["status"] == "pending"
        assert artifact["retry_state"]["attempt"] == 0
        assert artifact["retry_state"]["max_attempts"] == 3
        assert artifact["pending_write"]["validated"] is False

    def test_create_discovered_artifact_state(self):
        """Test creating discovered artifact state."""
        artifact = create_artifact_state(
            artifact_type="agent",
            label="my_agent",
            file_path="/path/to/agent.py",
            discovered=True  # Found via discovery
        )

        assert artifact["discovered"] is True
        assert artifact["type"] == "agent"


# =============================================================================
# ARTIFACT CRUD TESTS
# =============================================================================

class TestArtifactCRUD:
    """Test artifact Create, Read, Update, Delete operations."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_v2_crud_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def v2_state_with_artifacts(self, temp_workspace):
        """Create v2 state with some artifacts."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        # Add artifacts
        state, id1 = add_artifact(temp_workspace, "nugget", "nugget_one", "/path/one.nugget.js")
        state, id2 = add_artifact(temp_workspace, "nugget", "nugget_two", "/path/two.nugget.js")
        state, id3 = add_artifact(temp_workspace, "agent", "my_agent", "/path/agent.py")

        return state, [id1, id2, id3]

    def test_add_artifact(self, temp_workspace):
        """Test adding a new artifact."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        state, artifact_id = add_artifact(
            temp_workspace,
            artifact_type="nugget",
            label="my_first_nugget",
            file_path="/path/to/nugget.js"
        )

        assert len(state["artifacts"]) == 1
        assert artifact_id is not None

        artifact = get_artifact(state, artifact_id)
        assert artifact is not None
        assert artifact["label"] == "my_first_nugget"
        assert artifact["type"] == "nugget"

    def test_add_multiple_artifacts(self, temp_workspace):
        """Test adding multiple artifacts."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        state, id1 = add_artifact(temp_workspace, "nugget", "first")
        state, id2 = add_artifact(temp_workspace, "nugget", "second")
        state, id3 = add_artifact(temp_workspace, "agent", "third")

        assert len(state["artifacts"]) == 3
        assert id1 != id2 != id3

    def test_get_artifact_by_id(self, v2_state_with_artifacts):
        """Test getting artifact by ID."""
        state, artifact_ids = v2_state_with_artifacts

        artifact = get_artifact(state, artifact_ids[0])
        assert artifact is not None
        assert artifact["label"] == "nugget_one"

    def test_get_artifact_by_path(self, v2_state_with_artifacts):
        """Test getting artifact by file path (critical for hooks)."""
        state, artifact_ids = v2_state_with_artifacts

        # Exact path match
        artifact = get_artifact_by_path(state, "/path/one.nugget.js")
        assert artifact is not None
        assert artifact["label"] == "nugget_one"

        # Different artifact
        artifact = get_artifact_by_path(state, "/path/agent.py")
        assert artifact is not None
        assert artifact["label"] == "my_agent"

    def test_get_artifact_by_path_not_found(self, v2_state_with_artifacts):
        """Test get_artifact_by_path returns None for unknown path."""
        state, _ = v2_state_with_artifacts

        artifact = get_artifact_by_path(state, "/unknown/path.js")
        assert artifact is None

    def test_get_artifact_by_label(self, v2_state_with_artifacts):
        """Test getting artifact by label."""
        state, _ = v2_state_with_artifacts

        artifact = get_artifact_by_label(state, "nugget_two")
        assert artifact is not None
        assert artifact["label"] == "nugget_two"

        # Case insensitive
        artifact = get_artifact_by_label(state, "NUGGET_TWO")
        assert artifact is not None

    def test_set_and_get_active_artifact(self, temp_workspace, v2_state_with_artifacts):
        """Test setting and getting active artifact."""
        state, artifact_ids = v2_state_with_artifacts

        # Set active
        set_active_artifact(temp_workspace, artifact_ids[1])
        state = load_state(temp_workspace)

        # Get active
        active = get_active_artifact(state)
        assert active is not None
        assert active["artifact_id"] == artifact_ids[1]
        assert active["label"] == "nugget_two"

    def test_list_artifacts(self, v2_state_with_artifacts):
        """Test listing all artifacts."""
        state, artifact_ids = v2_state_with_artifacts

        all_artifacts = list_artifacts(state)
        assert len(all_artifacts) == 3

    def test_list_artifacts_filtered_by_type(self, v2_state_with_artifacts):
        """Test filtering artifacts by type."""
        state, _ = v2_state_with_artifacts

        nuggets = list_artifacts(state, artifact_type="nugget")
        assert len(nuggets) == 2

        agents = list_artifacts(state, artifact_type="agent")
        assert len(agents) == 1

    def test_remove_artifact(self, temp_workspace, v2_state_with_artifacts):
        """Test removing artifact from tracking."""
        state, artifact_ids = v2_state_with_artifacts

        # Remove one
        state = remove_artifact(temp_workspace, artifact_ids[0])

        assert len(state["artifacts"]) == 2
        assert get_artifact(state, artifact_ids[0]) is None

    def test_remove_active_artifact_clears_active(self, temp_workspace, v2_state_with_artifacts):
        """Test that removing active artifact clears active_artifact_id."""
        state, artifact_ids = v2_state_with_artifacts

        # Set active
        set_active_artifact(temp_workspace, artifact_ids[0])

        # Remove it
        state = remove_artifact(temp_workspace, artifact_ids[0])

        assert state["active_artifact_id"] is None


# =============================================================================
# PER-ARTIFACT UPDATE TESTS
# =============================================================================

class TestPerArtifactUpdates:
    """Test per-artifact state updates."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_v2_update_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def workspace_with_artifact(self, temp_workspace):
        """Create workspace with a single artifact."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)
        state, artifact_id = add_artifact(
            temp_workspace, "nugget", "test_nugget", "/path/test.nugget.js"
        )
        return temp_workspace, artifact_id

    def test_update_artifact_step(self, workspace_with_artifact):
        """Test updating artifact workflow step."""
        workspace, artifact_id = workspace_with_artifact

        state = update_artifact_step(
            workspace, artifact_id, WorkflowStep.SEARCH_FUNCTIONS, "passed"
        )

        artifact = get_artifact(state, artifact_id)
        assert artifact["workflow_step"] == WorkflowStep.SEARCH_FUNCTIONS.value
        assert len(artifact["steps_completed"]) == 1
        assert artifact["steps_completed"][0]["step"] == WorkflowStep.SEARCH_FUNCTIONS.value

    def test_update_artifact_step_to_complete(self, workspace_with_artifact):
        """Test that completing workflow sets status to completed."""
        workspace, artifact_id = workspace_with_artifact

        state = update_artifact_step(
            workspace, artifact_id, WorkflowStep.COMPLETE, "passed"
        )

        artifact = get_artifact(state, artifact_id)
        assert artifact["status"] == "completed"

    def test_update_artifact_intent(self, workspace_with_artifact):
        """Test updating artifact intent."""
        workspace, artifact_id = workspace_with_artifact

        state = update_artifact_intent(
            workspace, artifact_id,
            user_requirement="Send newsletter emails",
            detected_intent="newsletter",
            discovered_functions=["ezMail", "ezLog"],
            required_functions=["ezMail"]
        )

        artifact = get_artifact(state, artifact_id)
        assert artifact["intent"]["user_requirement"] == "Send newsletter emails"
        assert artifact["intent"]["detected_intent"] == "newsletter"
        assert "ezMail" in artifact["intent"]["discovered_functions"]

    def test_update_artifact_code(self, workspace_with_artifact):
        """Test updating artifact code."""
        workspace, artifact_id = workspace_with_artifact

        state = update_artifact_code(
            workspace, artifact_id,
            code="(function(data) { return 'hello'; })()",
            validated=True,
            nugget_id="nug-12345"
        )

        artifact = get_artifact(state, artifact_id)
        assert artifact["artifact_data"]["code"] is not None
        assert artifact["artifact_data"]["validated"] is True
        assert artifact["artifact_data"]["nugget_id"] == "nug-12345"

    def test_update_artifact_pending_write(self, workspace_with_artifact):
        """Test updating artifact pending write."""
        workspace, artifact_id = workspace_with_artifact

        state = update_artifact_pending_write(
            workspace, artifact_id,
            file_path="/output/test.nugget.js",
            content="(function(data) {})()",
            validated=True
        )

        artifact = get_artifact(state, artifact_id)
        assert artifact["pending_write"]["file_path"] == "/output/test.nugget.js"
        assert artifact["pending_write"]["validated"] is True
        # Also updates main file_path
        assert artifact["file_path"] == "/output/test.nugget.js"

    def test_update_artifact_retry(self, workspace_with_artifact):
        """Test adding retry errors to artifact."""
        workspace, artifact_id = workspace_with_artifact

        # First error
        state = update_artifact_retry(
            workspace, artifact_id,
            error_message="Syntax error on line 5",
            fix_suggestion="Add missing semicolon"
        )

        artifact = get_artifact(state, artifact_id)
        assert artifact["retry_state"]["attempt"] == 1
        assert len(artifact["retry_state"]["errors"]) == 1
        assert can_artifact_retry(artifact) is True

        # Add more errors
        update_artifact_retry(workspace, artifact_id, "Error 2")
        state = update_artifact_retry(workspace, artifact_id, "Error 3")

        artifact = get_artifact(state, artifact_id)
        assert artifact["retry_state"]["attempt"] == 3
        assert can_artifact_retry(artifact) is False  # Max attempts reached

    def test_reset_artifact_retry(self, workspace_with_artifact):
        """Test resetting artifact retry state."""
        workspace, artifact_id = workspace_with_artifact

        # Add errors
        update_artifact_retry(workspace, artifact_id, "Error 1")
        update_artifact_retry(workspace, artifact_id, "Error 2")

        # Reset
        state = reset_artifact_retry(workspace, artifact_id)

        artifact = get_artifact(state, artifact_id)
        assert artifact["retry_state"]["attempt"] == 0
        assert len(artifact["retry_state"]["errors"]) == 0


# =============================================================================
# V1 TO V2 MIGRATION TESTS
# =============================================================================

class TestMigration:
    """Test migration from v1.0 to v2.0 state."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_migration_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_migrate_empty_v1_state(self, temp_workspace):
        """Test migrating empty v1 state."""
        # Create v1 state
        v1_state = create_empty_state(temp_workspace)
        save_state(temp_workspace, v1_state)

        # Migrate
        v2_state = migrate_v1_to_v2(temp_workspace)

        assert v2_state["version"] == "2.0"
        assert len(v2_state["artifacts"]) == 0  # No artifact to migrate
        assert v2_state["_migrated_from_v1"] is True

    def test_migrate_v1_with_credentials(self, temp_workspace):
        """Test that credentials are preserved during migration."""
        # Create v1 state with credentials
        v1_state = create_empty_state(temp_workspace)
        v1_state["credentials"]["jwt_provided"] = True
        v1_state["credentials"]["agent_id"] = "test-agent-id-123"
        v1_state["credentials"]["env"] = "QA"
        v1_state["credentials"]["env_file_written"] = True
        save_state(temp_workspace, v1_state)

        # Migrate
        v2_state = migrate_v1_to_v2(temp_workspace)

        assert v2_state["credentials"]["jwt_provided"] is True
        assert v2_state["credentials"]["agent_id"] == "test-agent-id-123"
        assert v2_state["credentials"]["env"] == "QA"
        assert v2_state["credentials"]["env_file_written"] is True

    def test_migrate_v1_with_artifact(self, temp_workspace):
        """Test migrating v1 state with artifact becomes array entry."""
        # Create v1 state with artifact data
        v1_state = create_empty_state(temp_workspace)
        v1_state["credentials"]["jwt_provided"] = True
        v1_state["artifact"]["type"] = "nugget"
        v1_state["artifact"]["code"] = "(function(data) {})()"
        v1_state["artifact"]["file_path"] = "/test/nugget.js"
        v1_state["intent"]["user_requirement"] = "test requirement"
        v1_state["intent"]["detected_intent"] = "newsletter"
        v1_state["pending_write"]["file_path"] = "/test/nugget.js"
        v1_state["pending_write"]["validated"] = True
        v1_state["current_step"] = WorkflowStep.READY_TO_WRITE.value
        save_state(temp_workspace, v1_state)

        # Migrate
        v2_state = migrate_v1_to_v2(temp_workspace)

        assert len(v2_state["artifacts"]) == 1
        artifact = v2_state["artifacts"][0]
        assert artifact["type"] == "nugget"
        assert artifact["intent"]["user_requirement"] == "test requirement"
        assert artifact["pending_write"]["validated"] is True
        assert artifact["workflow_step"] == WorkflowStep.READY_TO_WRITE.value
        assert v2_state["active_artifact_id"] == artifact["artifact_id"]

    def test_migrate_preserves_v1_backup(self, temp_workspace):
        """Test that original v1 state is preserved in backup."""
        v1_state = create_empty_state(temp_workspace)
        v1_state["credentials"]["agent_id"] = "backup-test-id"
        save_state(temp_workspace, v1_state)

        v2_state = migrate_v1_to_v2(temp_workspace)

        assert "_v1_backup" in v2_state
        assert v2_state["_v1_backup"]["credentials"]["agent_id"] == "backup-test-id"

    def test_migrate_already_v2_is_noop(self, temp_workspace):
        """Test that migrating v2 state does nothing."""
        v2_state = create_empty_state_v2(temp_workspace)
        v2_state, artifact_id = add_artifact(temp_workspace, "nugget", "test")
        original_artifact_count = len(v2_state["artifacts"])

        # Try to migrate again
        v2_state_again = migrate_v1_to_v2(temp_workspace)

        assert len(v2_state_again["artifacts"]) == original_artifact_count

    def test_add_artifact_auto_migrates_v1(self, temp_workspace):
        """Test that add_artifact auto-migrates v1 state."""
        # Create v1 state
        v1_state = create_empty_state(temp_workspace)
        save_state(temp_workspace, v1_state)

        # Add artifact (should auto-migrate)
        state, artifact_id = add_artifact(temp_workspace, "nugget", "new_nugget")

        assert state["version"] == "2.0"
        assert len(state["artifacts"]) == 1


# =============================================================================
# BACKWARDS COMPATIBILITY TESTS
# =============================================================================

class TestBackwardsCompatibility:
    """Test backwards compatibility helpers."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_compat_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_get_legacy_artifact_from_v1(self, temp_workspace):
        """Test get_legacy_artifact works with v1 state."""
        v1_state = create_empty_state(temp_workspace)
        v1_state["artifact"]["type"] = "nugget"
        v1_state["artifact"]["code"] = "test code"

        legacy = get_legacy_artifact(v1_state)

        assert legacy["artifact"]["type"] == "nugget"
        assert legacy["artifact"]["code"] == "test code"

    def test_get_legacy_artifact_from_v2(self, temp_workspace):
        """Test get_legacy_artifact converts v2 active artifact to v1 format."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        state, artifact_id = add_artifact(temp_workspace, "nugget", "test")
        set_active_artifact(temp_workspace, artifact_id)

        state = update_artifact_code(temp_workspace, artifact_id, code="v2 code", validated=True)
        state = update_artifact_intent(temp_workspace, artifact_id, user_requirement="v2 requirement")

        state = load_state(temp_workspace)
        legacy = get_legacy_artifact(state)

        assert legacy["artifact"]["code"] == "v2 code"
        assert legacy["artifact"]["validated"] is True
        assert legacy["intent"]["user_requirement"] == "v2 requirement"

    def test_validate_state_for_write_v2(self, temp_workspace):
        """Test v2 write validation checks artifact by path."""
        state = create_empty_state_v2(temp_workspace)
        state["credentials"]["env_file_written"] = True
        save_state(temp_workspace, state)

        state, artifact_id = add_artifact(
            temp_workspace, "nugget", "test", "/path/test.nugget.js"
        )

        # Not validated yet
        is_valid, error = validate_state_for_write_v2(temp_workspace, "/path/test.nugget.js")
        assert not is_valid
        assert "not been validated" in error

        # Mark validated
        update_artifact_pending_write(temp_workspace, artifact_id, validated=True)

        is_valid, error = validate_state_for_write_v2(temp_workspace, "/path/test.nugget.js")
        assert is_valid


# =============================================================================
# MULTI-ARTIFACT WORKFLOW TESTS
# =============================================================================

class TestMultiArtifactWorkflow:
    """Test multi-artifact workflow scenarios."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_multi_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_independent_artifact_progress(self, temp_workspace):
        """Test that artifacts have independent progress."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        # Add two artifacts
        state, id1 = add_artifact(temp_workspace, "nugget", "nugget_1")
        state, id2 = add_artifact(temp_workspace, "nugget", "nugget_2")

        # Progress first artifact
        update_artifact_step(temp_workspace, id1, WorkflowStep.SEARCH_FUNCTIONS)
        update_artifact_step(temp_workspace, id1, WorkflowStep.CREATE_ARTIFACT)
        update_artifact_step(temp_workspace, id1, WorkflowStep.COMPLETE)

        # Check states are independent
        state = load_state(temp_workspace)
        artifact1 = get_artifact(state, id1)
        artifact2 = get_artifact(state, id2)

        assert artifact1["workflow_step"] == WorkflowStep.COMPLETE.value
        assert artifact1["status"] == "completed"
        assert artifact2["workflow_step"] == WorkflowStep.INIT.value
        assert artifact2["status"] == "pending"

    def test_independent_retry_counters(self, temp_workspace):
        """Test that retry counters are per-artifact."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        state, id1 = add_artifact(temp_workspace, "nugget", "nugget_1")
        state, id2 = add_artifact(temp_workspace, "nugget", "nugget_2")

        # Add errors to first artifact
        update_artifact_retry(temp_workspace, id1, "Error 1")
        update_artifact_retry(temp_workspace, id1, "Error 2")

        # Check counters are independent
        state = load_state(temp_workspace)
        artifact1 = get_artifact(state, id1)
        artifact2 = get_artifact(state, id2)

        assert artifact1["retry_state"]["attempt"] == 2
        assert artifact2["retry_state"]["attempt"] == 0

    def test_shared_credentials(self, temp_workspace):
        """Test that credentials are shared across all artifacts."""
        state = create_empty_state_v2(temp_workspace)
        state["credentials"]["jwt_provided"] = True
        state["credentials"]["agent_id"] = "shared-agent-id"
        state["credentials"]["env_file_written"] = True
        save_state(temp_workspace, state)

        # Add multiple artifacts
        state, id1 = add_artifact(temp_workspace, "nugget", "nugget_1")
        state, id2 = add_artifact(temp_workspace, "nugget", "nugget_2")

        # Credentials should be at state level, not per-artifact
        state = load_state(temp_workspace)
        assert state["credentials"]["jwt_provided"] is True
        assert state["credentials"]["agent_id"] == "shared-agent-id"

        # All artifacts inherit same credentials
        artifact1 = get_artifact(state, id1)
        artifact2 = get_artifact(state, id2)
        # Artifacts don't have their own credentials
        assert "credentials" not in artifact1 or artifact1.get("credentials") is None

    def test_switch_active_artifact(self, temp_workspace):
        """Test switching between active artifacts."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        state, id1 = add_artifact(temp_workspace, "nugget", "nugget_1")
        state, id2 = add_artifact(temp_workspace, "nugget", "nugget_2")

        # Set first active
        set_active_artifact(temp_workspace, id1)
        state = load_state(temp_workspace)
        assert get_active_artifact(state)["artifact_id"] == id1

        # Switch to second
        set_active_artifact(temp_workspace, id2)
        state = load_state(temp_workspace)
        assert get_active_artifact(state)["artifact_id"] == id2


# =============================================================================
# HOOK SIMULATION TESTS
# =============================================================================

class TestHookSimulation:
    """Test artifact lookup as hooks would use it."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_hook_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_hook_finds_artifact_by_file_path(self, temp_workspace):
        """Simulate pre-write hook looking up artifact by path."""
        state = create_empty_state_v2(temp_workspace)
        state["credentials"]["env_file_written"] = True
        save_state(temp_workspace, state)

        # Add artifacts with different paths
        state, id1 = add_artifact(
            temp_workspace, "nugget", "email_nugget",
            "/workspace/nuggets/email.nugget.js"
        )
        state, id2 = add_artifact(
            temp_workspace, "nugget", "sms_nugget",
            "/workspace/nuggets/sms.nugget.js"
        )

        # Mark one as validated
        update_artifact_pending_write(temp_workspace, id1, validated=True)

        # Simulate hook checking email file
        state = load_state(temp_workspace)
        artifact = get_artifact_by_path(state, "/workspace/nuggets/email.nugget.js")
        assert artifact is not None
        assert artifact["label"] == "email_nugget"
        assert artifact["pending_write"]["validated"] is True

        # Simulate hook checking sms file
        artifact = get_artifact_by_path(state, "/workspace/nuggets/sms.nugget.js")
        assert artifact is not None
        assert artifact["label"] == "sms_nugget"
        assert artifact["pending_write"]["validated"] is False

    def test_hook_fallback_to_active_artifact(self, temp_workspace):
        """Test hook fallback when path not found."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        state, artifact_id = add_artifact(temp_workspace, "nugget", "active_nugget")
        set_active_artifact(temp_workspace, artifact_id)

        state = load_state(temp_workspace)

        # Unknown path should return None
        artifact = get_artifact_by_path(state, "/unknown/path.js")
        assert artifact is None

        # But we can fall back to active
        active = get_active_artifact(state)
        assert active is not None
        assert active["label"] == "active_nugget"

    def test_hook_updates_correct_artifact(self, temp_workspace):
        """Test that post-write hook updates the correct artifact."""
        state = create_empty_state_v2(temp_workspace)
        state["credentials"]["env_file_written"] = True
        save_state(temp_workspace, state)

        # Add two artifacts
        state, id1 = add_artifact(
            temp_workspace, "nugget", "first",
            "/workspace/first.nugget.js"
        )
        state, id2 = add_artifact(
            temp_workspace, "nugget", "second",
            "/workspace/second.nugget.js"
        )

        # Simulate post-write hook updating first artifact
        state = load_state(temp_workspace)
        artifact = get_artifact_by_path(state, "/workspace/first.nugget.js")
        update_artifact_step(temp_workspace, artifact["artifact_id"], WorkflowStep.COMPLETE)

        # Verify only first was updated
        state = load_state(temp_workspace)
        artifact1 = get_artifact(state, id1)
        artifact2 = get_artifact(state, id2)

        assert artifact1["workflow_step"] == WorkflowStep.COMPLETE.value
        assert artifact2["workflow_step"] == WorkflowStep.INIT.value


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_edge_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_get_artifact_invalid_id(self, temp_workspace):
        """Test getting artifact with invalid ID returns None."""
        state = create_empty_state_v2(temp_workspace)
        artifact = get_artifact(state, "invalid-id-12345")
        assert artifact is None

    def test_set_active_artifact_invalid_id_raises(self, temp_workspace):
        """Test setting active artifact with invalid ID raises."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        with pytest.raises(ValueError):
            set_active_artifact(temp_workspace, "invalid-id")

    def test_update_artifact_step_invalid_id_raises(self, temp_workspace):
        """Test updating artifact step with invalid ID raises."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        with pytest.raises(ValueError):
            update_artifact_step(temp_workspace, "invalid-id", WorkflowStep.INIT)

    def test_empty_artifacts_list(self, temp_workspace):
        """Test operations on empty artifacts list."""
        state = create_empty_state_v2(temp_workspace)

        assert list_artifacts(state) == []
        assert get_active_artifact(state) is None
        assert get_artifact_by_path(state, "/any/path.js") is None

    def test_path_normalization(self, temp_workspace):
        """Test that paths are normalized for comparison."""
        state = create_empty_state_v2(temp_workspace)
        save_state(temp_workspace, state)

        # Add with one path format
        state, artifact_id = add_artifact(
            temp_workspace, "nugget", "test",
            "/workspace/nuggets/test.nugget.js"
        )

        # Find with slightly different format
        state = load_state(temp_workspace)
        artifact = get_artifact_by_path(state, "/workspace/nuggets//test.nugget.js")
        assert artifact is not None

        artifact = get_artifact_by_path(state, "/workspace/./nuggets/test.nugget.js")
        assert artifact is not None
