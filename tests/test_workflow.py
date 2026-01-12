"""
Tests for Deterministic Workflow Enforcement

Tests the workflow orchestrator, state management, and hook integration.
Verifies that the workflow is mandatory and cannot be bypassed.
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
    get_or_create_state,
    update_step,
    update_credentials,
    update_intent,
    update_artifact,
    update_pending_write,
    add_retry_error,
    is_step_completed,
    get_missing_steps,
    can_retry,
    reset_state,
    validate_state_for_write,
    mark_env_file_written,
    WorkflowStep,
    WorkflowStatus,
    MANDATORY_STEPS
)

from tools.workflow import (
    handle_eliza_workflow,
    validate_jwt_format,
    validate_agent_id_format,
    validate_initiative_id_format
)

from search.search import (
    smart_search,
    detect_intents,
    get_functions_for_intent
)


# =============================================================================
# WORKFLOW STATE TESTS
# =============================================================================

class TestWorkflowState:
    """Test workflow state management."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_workflow_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_create_empty_state(self, temp_workspace):
        """Test creating a new empty workflow state."""
        state = create_empty_state(temp_workspace)

        assert state["version"] == "1.0"
        assert state["current_step"] == WorkflowStep.INIT.value
        assert len(state["steps_completed"]) == 0
        assert state["credentials"]["jwt_provided"] == False
        assert state["retry_state"]["attempt"] == 0

    def test_get_or_create_state(self, temp_workspace):
        """Test get_or_create_state creates new state if none exists."""
        state = get_or_create_state(temp_workspace)

        assert state is not None
        assert "session_id" in state

        # State file should now exist
        state_file = os.path.join(temp_workspace, ".eliza", "workflow_state.json")
        assert os.path.exists(state_file)

    def test_update_step(self, temp_workspace):
        """Test updating workflow step."""
        get_or_create_state(temp_workspace)

        state = update_step(temp_workspace, WorkflowStep.CHECK_CREDENTIALS, "passed")

        assert state["current_step"] == WorkflowStep.CHECK_CREDENTIALS.value
        assert is_step_completed(state, WorkflowStep.CHECK_CREDENTIALS)

    def test_update_credentials(self, temp_workspace):
        """Test updating credentials."""
        get_or_create_state(temp_workspace)

        state = update_credentials(
            temp_workspace,
            jwt_token="test-jwt",
            agent_id="12345678-1234-1234-1234-123456789abc",
            env="QA"
        )

        assert state["credentials"]["jwt_provided"] == True
        assert state["credentials"]["agent_id"] == "12345678-1234-1234-1234-123456789abc"
        assert state["credentials"]["env"] == "QA"

    def test_get_missing_steps(self, temp_workspace):
        """Test getting list of missing mandatory steps."""
        state = get_or_create_state(temp_workspace)

        missing = get_missing_steps(state)

        # Should have all mandatory steps missing
        assert len(missing) == len(MANDATORY_STEPS)
        assert WorkflowStep.CHECK_CREDENTIALS.value in missing
        assert WorkflowStep.SEARCH_FUNCTIONS.value in missing

    def test_retry_state(self, temp_workspace):
        """Test retry state management."""
        state = get_or_create_state(temp_workspace)

        # Add first error
        state = add_retry_error(temp_workspace, "First error", "Fix suggestion")
        assert state["retry_state"]["attempt"] == 1
        assert can_retry(state)

        # Add two more errors
        add_retry_error(temp_workspace, "Second error")
        state = add_retry_error(temp_workspace, "Third error")

        assert state["retry_state"]["attempt"] == 3
        assert not can_retry(state)  # Max attempts reached

    def test_validate_state_for_write_incomplete(self, temp_workspace):
        """Test that incomplete workflow state blocks writes."""
        get_or_create_state(temp_workspace)

        is_valid, error = validate_state_for_write(temp_workspace)

        assert not is_valid
        assert "Incomplete workflow" in error or "Missing steps" in error

    def test_validate_state_for_write_complete(self, temp_workspace):
        """Test that complete workflow state allows writes."""
        get_or_create_state(temp_workspace)

        # Complete all mandatory steps
        for step in MANDATORY_STEPS:
            update_step(temp_workspace, step, "passed")

        # Mark env file written
        mark_env_file_written(temp_workspace)

        # Set pending write as validated
        update_pending_write(temp_workspace, "/test/file.js", "code", True)

        is_valid, error = validate_state_for_write(temp_workspace)

        assert is_valid
        assert error == ""


# =============================================================================
# VALIDATION HELPER TESTS
# =============================================================================

class TestValidationHelpers:
    """Test input validation helpers."""

    def test_validate_jwt_format_valid(self):
        """Test valid JWT format."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        valid, error = validate_jwt_format(jwt)
        assert valid
        assert error == ""

    def test_validate_jwt_format_placeholder(self):
        """Test placeholder JWT is rejected."""
        valid, error = validate_jwt_format("{YOUR_JWT_HERE}")
        assert not valid
        assert "placeholder" in error.lower()

    def test_validate_jwt_format_too_short(self):
        """Test short JWT is rejected."""
        valid, error = validate_jwt_format("abc")
        assert not valid
        assert "short" in error.lower()

    def test_validate_agent_id_format_valid(self):
        """Test valid agent ID format."""
        valid, error = validate_agent_id_format("12345678-1234-1234-1234-123456789abc")
        assert valid
        assert error == ""

    def test_validate_agent_id_format_placeholder(self):
        """Test placeholder agent ID is rejected."""
        valid, error = validate_agent_id_format("{AGENT_ID}")
        assert not valid
        assert "placeholder" in error.lower()

    def test_validate_agent_id_format_invalid(self):
        """Test invalid agent ID format is rejected."""
        valid, error = validate_agent_id_format("not-a-uuid")
        assert not valid
        assert "UUID" in error


# =============================================================================
# WORKFLOW ORCHESTRATOR TESTS
# =============================================================================

class TestWorkflowOrchestrator:
    """Test the workflow orchestrator tool."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_workflow_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_workflow_status(self, temp_workspace):
        """Test getting workflow status."""
        result = await handle_eliza_workflow({
            "action": "status",
            "workspace_path": temp_workspace
        })

        assert result["status"] == "STATUS"
        assert result["current_step"] == WorkflowStep.INIT.value
        assert len(result["missing_steps"]) > 0

    @pytest.mark.asyncio
    async def test_workflow_start_missing_requirement(self, temp_workspace):
        """Test starting workflow without requirement."""
        result = await handle_eliza_workflow({
            "action": "start",
            "workspace_path": temp_workspace
        })

        assert result["status"] == "ERROR"
        assert "requirement" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_workflow_start_needs_credentials(self, temp_workspace):
        """Test starting workflow requests credentials."""
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Create a newsletter agent",
            "workspace_path": temp_workspace
        })

        assert result["status"] == WorkflowStatus.NEED_CREDENTIALS.value
        assert "jwt" in str(result).lower() or "credentials" in str(result).lower()

    @pytest.mark.asyncio
    async def test_workflow_reset(self, temp_workspace):
        """Test resetting workflow state."""
        # Create some state first
        get_or_create_state(temp_workspace)
        update_step(temp_workspace, WorkflowStep.CHECK_CREDENTIALS, "passed")

        # Reset
        result = await handle_eliza_workflow({
            "action": "reset",
            "workspace_path": temp_workspace
        })

        assert result["status"] == "RESET"

        # Verify state is reset
        state = get_or_create_state(temp_workspace)
        assert len(state["steps_completed"]) == 0

    @pytest.mark.asyncio
    async def test_workflow_with_valid_credentials(self, temp_workspace):
        """Test workflow progression with valid credentials."""
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Create a newsletter agent",
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "workspace_path": temp_workspace
        })

        # Should progress to searching or creating
        assert result["status"] in [
            WorkflowStatus.CREATING.value,
            WorkflowStatus.SEARCHING.value,
            "SEARCHING",
            "CREATING"
        ] or "discovered_functions" in str(result)


# =============================================================================
# INTENT DETECTION TESTS
# =============================================================================

class TestIntentDetection:
    """Test intent detection from natural language."""

    def test_detect_newsletter_intent(self):
        """Test detecting newsletter intent."""
        intents = detect_intents("make me a newsletter agent")

        assert len(intents) > 0
        assert intents[0]["intent"] == "newsletter"
        assert "ezMail" in intents[0]["requires"]

    def test_detect_research_intent(self):
        """Test detecting research intent."""
        intents = detect_intents("deep research on the internet")

        assert len(intents) > 0
        assert intents[0]["intent"] == "deep_research"
        assert "ezInternetSearch" in intents[0]["requires"]

    def test_detect_no_intent(self):
        """Test no intent detected for non-Eliza query."""
        intents = detect_intents("hello world")

        assert len(intents) == 0

    def test_get_functions_for_intent(self):
        """Test getting functions for detected intent."""
        required, optional, intent = get_functions_for_intent("send daily newsletter emails")

        assert intent == "newsletter"
        assert "ezMail" in required
        assert len(optional) > 0


# =============================================================================
# SMART SEARCH TESTS
# =============================================================================

class TestSmartSearch:
    """Test the smart search combining intent and keywords."""

    def test_smart_search_with_intent(self):
        """Test smart search finds intent and functions."""
        result = smart_search("create a newsletter agent")

        assert result["has_intent"]
        assert result["detected_intent"] == "newsletter"
        assert "ezMail" in result["required_functions"]
        assert len(result["all_functions"]) > 0

    def test_smart_search_keyword_fallback(self):
        """Test smart search falls back to keywords."""
        result = smart_search("ezLog debug")

        # Should find ezLog via keywords even if no intent match
        assert "ezLog" in result["all_functions"]

    def test_smart_search_combined(self):
        """Test smart search combines intent and keyword results."""
        result = smart_search("research news and send email digest")

        # Should find both research and email functions
        all_funcs = result["all_functions"]
        assert "ezMail" in all_funcs or "ezInternetSearch" in all_funcs


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestWorkflowIntegration:
    """Integration tests for the full workflow."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="eliza_workflow_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_full_workflow_happy_path(self, temp_workspace):
        """Test complete workflow from start to ready-to-write."""
        # Step 1: Start workflow
        result = await handle_eliza_workflow({
            "action": "start",
            "requirement": "Send daily newsletter emails",
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "workspace_path": temp_workspace
        })

        # Should be at creating/searching stage
        assert "discovered_functions" in str(result) or "CREATING" in str(result)

        # Verify state was created
        state = get_or_create_state(temp_workspace)
        assert state["credentials"]["jwt_provided"]

    @pytest.mark.asyncio
    async def test_workflow_retry_after_failure(self, temp_workspace):
        """Test retry workflow after validation failure."""
        # Setup: Create state and mark static validation failed
        get_or_create_state(temp_workspace)
        update_credentials(
            temp_workspace,
            jwt_token="test-jwt",
            agent_id="12345678-1234-1234-1234-123456789abc"
        )
        mark_env_file_written(temp_workspace)
        for step in [WorkflowStep.CHECK_CREDENTIALS, WorkflowStep.WRITE_ENV_FILE,
                     WorkflowStep.SEARCH_FUNCTIONS, WorkflowStep.CREATE_ARTIFACT]:
            update_step(temp_workspace, step, "passed")

        # Mark static validation failed
        update_step(temp_workspace, WorkflowStep.STATIC_VALIDATION, "failed", {"errors": ["Test error"]})
        add_retry_error(temp_workspace, "Test error", "Fix the code")

        # Call retry
        result = await handle_eliza_workflow({
            "action": "retry",
            "workspace_path": temp_workspace
        })

        # Should provide retry info
        assert "error" in str(result).lower() or "retry" in str(result).lower()
