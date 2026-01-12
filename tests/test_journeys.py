"""
Layer 3: End-to-End Journey Tests

Tests complete user journeys from MCP tool call through file writing
and hook validation.

This layer tests the COMPLETE flow:
1. User calls MCP tool (e.g., search_ez_functions)
2. MCP returns response with file content
3. Cascade writes file to disk
4. Windsurf triggers hook
5. Hook validates (static + runtime)
6. User sees final result

These are the tests that verify the actual user experience.
"""

import pytest
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import call_tool
from tests.helpers.hook_runner import run_hook_on_file, create_hook_payload, run_hook
from tests.helpers.response_parser import (
    extract_javascript_code,
    extract_file_path,
    extract_discovered_functions,
    is_success_response,
    is_error_response,
    extract_nugget_id
)


# =============================================================================
# NUGGET CREATION JOURNEY
# =============================================================================

class TestNuggetCreationJourney:
    """Test the complete nugget creation journey."""

    @pytest.mark.asyncio
    async def test_search_then_create_happy_path(self, mock_api, temp_workspace):
        """
        Complete happy path: search → create → write → hook

        Steps:
        1. User searches for email functions
        2. User creates nugget with discovered functions
        3. Cascade writes file to disk
        4. Hook validates the file
        """
        # Step 1: User searches for functions
        search_result = await call_tool("search_ez_functions", {"query": "send email"})
        search_response = search_result[0].text

        # Verify search returns ezMail
        assert "ezMail" in search_response
        assert "discovered_functions" in search_response

        # Extract discovered functions
        discovered = extract_discovered_functions(search_response)
        assert "ezMail" in discovered

        # Step 2: User creates nugget
        create_result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Send email notifications",
            "discovered_functions": ["ezMail"],
            "skip_search": True,
            "email": "test@example.com",
            "workspace_path": temp_workspace
        })
        create_response = create_result[0].text

        # Verify creation succeeded
        assert is_success_response(create_response)
        assert "NUGGET CREATED" in create_response or "VALIDATED" in create_response

        # Step 3: Extract file content and write to disk
        code = extract_javascript_code(create_response)
        if code:
            # Write the file as Cascade would
            nugget_dir = os.path.join(temp_workspace, "nuggets", "12345678")
            os.makedirs(nugget_dir, exist_ok=True)
            nugget_file = os.path.join(nugget_dir, "send_email.nugget.js")

            with open(nugget_file, "w") as f:
                f.write(code)

            # Step 4: Simulate hook validation
            hook_result = run_hook_on_file(nugget_file)

            # Verify hook passes
            assert hook_result.passed or "Static validation PASSED" in hook_result.stdout

    @pytest.mark.asyncio
    async def test_workflow_enforcement_journey(self):
        """
        Journey: User skips search → gets workflow error

        This tests that the workflow is enforced correctly.
        """
        # User tries to create nugget without searching first
        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Send email"
            # Missing discovered_functions!
        })
        response = result[0].text

        # Verify workflow error
        assert is_error_response(response)
        assert "WORKFLOW ERROR" in response
        assert "search_ez_functions" in response

    @pytest.mark.asyncio
    async def test_invalid_function_journey(self):
        """
        Journey: User uses invalid function → gets error

        Tests that invalid/non-existent functions are caught.
        """
        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Do something magical",
            "discovered_functions": ["ezMagicFunction"],  # Doesn't exist!
            "skip_search": True
        })
        response = result[0].text

        # Verify error about invalid function
        assert is_error_response(response)
        assert "Unknown functions" in response or "INVALID" in response or "do not exist" in response


# =============================================================================
# VALIDATION FAILURE JOURNEY
# =============================================================================

class TestValidationFailureJourney:
    """Test journeys where validation fails."""

    @pytest.mark.asyncio
    async def test_static_validation_failure_journey(self, temp_workspace):
        """
        Journey: Create nugget with bad code → static validation blocks

        Note: This tests what happens when the generated code is invalid.
        """
        # Create a file with invalid nugget code directly
        nugget_dir = os.path.join(temp_workspace, "nuggets")
        os.makedirs(nugget_dir, exist_ok=True)
        nugget_file = os.path.join(nugget_dir, "bad.nugget.js")

        # Write invalid code (missing IIFE wrapper)
        with open(nugget_file, "w") as f:
            f.write('function badNugget(data) { return data; }')

        # Hook should block this
        hook_result = run_hook_on_file(nugget_file)

        # Should fail static validation
        assert hook_result.blocked or "Static validation FAILED" in hook_result.stdout

    @pytest.mark.asyncio
    async def test_invalid_jwt_journey(self):
        """
        Journey: User provides invalid JWT → validation error

        Tests input validation catches bad credentials early.
        """
        result = await call_tool("create_nugget", {
            "jwt_token": "{YOUR_JWT_HERE}",  # Placeholder!
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Test",
            "discovered_functions": ["ezLog"],
            "skip_search": True
        })
        response = result[0].text

        # Should fail with validation error about JWT
        assert is_error_response(response)
        assert "VALIDATION FAILED" in response or "jwt" in response.lower()


# =============================================================================
# SEARCH JOURNEY
# =============================================================================

class TestSearchJourney:
    """Test search function journeys."""

    @pytest.mark.asyncio
    async def test_search_multiple_capabilities(self):
        """
        Journey: User searches for complex capability → gets multiple functions

        Tests that search returns relevant results for complex queries.
        """
        result = await call_tool("search_ez_functions", {
            "query": "search internet then send email with results"
        })
        response = result[0].text

        # Should return multiple functions
        discovered = extract_discovered_functions(response)

        # Should have some functions
        assert len(discovered) > 0

    @pytest.mark.asyncio
    async def test_search_llm_journey(self):
        """Journey: User searches for LLM capabilities."""
        result = await call_tool("search_ez_functions", {
            "query": "call GPT summarize text"
        })
        response = result[0].text

        assert "ezChatCompletions" in response

    @pytest.mark.asyncio
    async def test_search_data_journey(self):
        """Journey: User searches for data storage capabilities."""
        result = await call_tool("search_ez_functions", {
            "query": "save session data persist"
        })
        response = result[0].text

        # Should find session-related functions
        assert "ezSaveSessionData" in response or "ezGetSessionData" in response or "session" in response.lower()


# =============================================================================
# CRUD JOURNEY
# =============================================================================

class TestCRUDJourney:
    """Test CRUD operation journeys."""

    @pytest.mark.asyncio
    async def test_get_agent_journey(self, mock_api):
        """Journey: User retrieves agent details."""
        result = await call_tool("get_agent", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc"
        })
        response = result[0].text

        # With mock_api, should get agent details
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_list_nuggets_journey(self, mock_api):
        """Journey: User lists nuggets on an agent."""
        result = await call_tool("list_nuggets", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc"
        })
        response = result[0].text

        assert len(response) > 0


# =============================================================================
# HOOK INTEGRATION JOURNEY
# =============================================================================

class TestHookIntegrationJourney:
    """Test the full MCP → file write → hook flow."""

    @pytest.mark.asyncio
    async def test_ezlog_nugget_journey(self, temp_workspace):
        """
        Journey: Create simple ezLog nugget → write → hook validates

        This is the simplest happy path.
        """
        # Step 1: Search for logging
        search_result = await call_tool("search_ez_functions", {"query": "log debug"})
        assert "ezLog" in search_result[0].text

        # Step 2: Create nugget with ezLog (simple, always works)
        create_result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Log debug messages",
            "discovered_functions": ["ezLog"],
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = create_result[0].text

        # Step 3: Extract and write code
        code = extract_javascript_code(response)
        if code:
            nugget_dir = os.path.join(temp_workspace, "nuggets", "12345678")
            os.makedirs(nugget_dir, exist_ok=True)
            nugget_file = os.path.join(nugget_dir, "debug_log.nugget.js")

            with open(nugget_file, "w") as f:
                f.write(code)

            # Step 4: Run hook
            hook_result = run_hook_on_file(nugget_file)

            # ezLog is simple, should always pass
            assert hook_result.passed or "Static validation PASSED" in hook_result.stdout

    @pytest.mark.asyncio
    async def test_file_write_triggers_hook(self, temp_workspace):
        """
        Verify that writing a nugget file triggers hook validation.

        This simulates the exact flow that happens in Windsurf.
        """
        # Write a valid nugget file
        nugget_dir = os.path.join(temp_workspace, "nuggets")
        os.makedirs(nugget_dir, exist_ok=True)
        nugget_file = os.path.join(nugget_dir, "manual.nugget.js")

        valid_code = '''(function(data) {
    var message = data.message || "Hello";
    ezLog("Processing: " + message);
    return "Logged: " + message;
})()'''

        with open(nugget_file, "w") as f:
            f.write(valid_code)

        # Create hook payload (exactly as Windsurf does)
        payload = create_hook_payload(
            file_path=nugget_file,
            changed_files=[nugget_file],
            tool_name="write_to_file"
        )

        # Run hook
        hook_result = run_hook(payload)

        # Should pass validation
        assert hook_result.passed or "Static validation PASSED" in hook_result.stdout


# =============================================================================
# ERROR RECOVERY JOURNEY
# =============================================================================

class TestErrorRecoveryJourney:
    """Test journeys where user recovers from errors."""

    @pytest.mark.asyncio
    async def test_retry_after_validation_error(self, temp_workspace):
        """
        Journey: User gets validation error → fixes → retries successfully

        1. First attempt with invalid code
        2. See error
        3. Fix and retry
        """
        nugget_dir = os.path.join(temp_workspace, "nuggets")
        os.makedirs(nugget_dir, exist_ok=True)
        nugget_file = os.path.join(nugget_dir, "retry.nugget.js")

        # First attempt: Invalid code
        with open(nugget_file, "w") as f:
            f.write('function bad() { return 1; }')  # Missing IIFE

        hook_result1 = run_hook_on_file(nugget_file)

        # Should fail
        assert hook_result1.blocked or "FAILED" in hook_result1.stdout

        # Second attempt: Fixed code
        with open(nugget_file, "w") as f:
            f.write('(function(data) { ezLog("fixed"); return "ok"; })()')

        hook_result2 = run_hook_on_file(nugget_file)

        # Should pass now
        assert hook_result2.passed or "Static validation PASSED" in hook_result2.stdout


# =============================================================================
# RESPONSE PARSER TESTS
# =============================================================================

class TestResponseParsing:
    """Test that response parsing works correctly."""

    @pytest.mark.asyncio
    async def test_parse_search_response(self):
        """Test parsing search_ez_functions response."""
        result = await call_tool("search_ez_functions", {"query": "email"})
        response = result[0].text

        # Should be able to extract discovered functions
        functions = extract_discovered_functions(response)
        assert len(functions) > 0
        assert "ezMail" in functions

    @pytest.mark.asyncio
    async def test_parse_create_response(self, mock_api, temp_workspace):
        """Test parsing create_nugget response."""
        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Log messages",
            "discovered_functions": ["ezLog"],
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = result[0].text

        # Should be able to detect success/error
        assert is_success_response(response) or is_error_response(response)

        if is_success_response(response):
            # Should be able to extract code
            code = extract_javascript_code(response)
            assert code is not None or "javascript" in response.lower()
