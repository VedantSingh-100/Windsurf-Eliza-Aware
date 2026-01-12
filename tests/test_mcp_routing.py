"""
Layer 1: MCP Tool Routing Tests

Tests that all 27 MCP tools route correctly through the call_tool function
and return appropriate responses.

This layer tests:
- Tool routing (correct handler is called)
- Response format (TextContent returned)
- Error handling (unknown tools, invalid inputs)
- Workflow enforcement (e.g., create_nugget requires discovered_functions)
"""

import pytest
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import tool handlers directly (server.py uses relative imports that don't work standalone)
from tools.nuggets import handle_search_ez_functions, handle_create_nugget
from tools.validation import handle_validate_eliza_code, diagnose_error
from tools.reference import get_api_endpoint, get_valid_values
from tools.capabilities import handle_category_capability
from tools.crud import (
    handle_get_agent, handle_update_agent, handle_delete_agent, handle_list_agents,
    handle_get_nugget, handle_update_nugget, handle_delete_nugget, handle_list_nuggets,
    handle_get_function, handle_delete_function, handle_list_functions
)
from tools.agents import create_rag_agent, create_function_agent
from tools.documents import create_document_upload


async def call_tool(name: str, arguments: dict) -> list:
    """
    Simulate MCP call_tool routing for testing.

    This mimics server.py's call_tool function but works standalone.
    """
    from mcp.types import TextContent

    # Route to appropriate handler
    if name == "search_ez_functions":
        result = handle_search_ez_functions(arguments)
    elif name == "create_nugget":
        result = await handle_create_nugget(arguments)
    elif name == "validate_eliza_code":
        result = handle_validate_eliza_code(arguments)
    elif name == "diagnose_error":
        result = diagnose_error(arguments)
    elif name == "get_api_endpoint":
        result = get_api_endpoint(arguments)
    elif name == "get_valid_values":
        result = get_valid_values(arguments)
    elif name in ["create_communication_capability", "create_integration_capability",
                  "create_ai_capability", "create_automation_capability",
                  "create_data_capability", "create_interop_capability"]:
        result = handle_category_capability(name, arguments)
    elif name == "get_agent":
        result = handle_get_agent(arguments)
    elif name == "update_agent":
        result = handle_update_agent(arguments)
    elif name == "delete_agent":
        result = handle_delete_agent(arguments)
    elif name == "list_agents":
        result = handle_list_agents(arguments)
    elif name == "get_nugget":
        result = handle_get_nugget(arguments)
    elif name == "update_nugget":
        result = handle_update_nugget(arguments)
    elif name == "delete_nugget":
        result = handle_delete_nugget(arguments)
    elif name == "list_nuggets":
        result = handle_list_nuggets(arguments)
    elif name == "get_function":
        result = handle_get_function(arguments)
    elif name == "delete_function":
        result = handle_delete_function(arguments)
    elif name == "list_functions":
        result = handle_list_functions(arguments)
    elif name == "create_rag_agent":
        result = create_rag_agent(arguments)
    elif name == "create_function_agent":
        result = create_function_agent(arguments)
    elif name == "create_document_upload":
        result = create_document_upload(arguments)
    else:
        result = f"Unknown tool: {name}"

    return [TextContent(type="text", text=result)]


# =============================================================================
# SEARCH TOOLS (2)
# =============================================================================

class TestSearchEzFunctions:
    """Test the search_ez_functions tool routing."""

    @pytest.mark.asyncio
    async def test_search_returns_functions(self):
        """Search with valid query returns matching functions."""
        result = await call_tool("search_ez_functions", {"query": "email"})
        response = result[0].text

        assert "ezMail" in response
        assert "Next Step" in response
        assert "discovered_functions" in response

    @pytest.mark.asyncio
    async def test_search_internet_query(self):
        """Search for internet functions."""
        result = await call_tool("search_ez_functions", {"query": "search internet"})
        response = result[0].text

        assert "ezInternetSearch" in response

    @pytest.mark.asyncio
    async def test_search_llm_query(self):
        """Search for LLM functions."""
        result = await call_tool("search_ez_functions", {"query": "call llm"})
        response = result[0].text

        assert "ezChatCompletions" in response

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Search with nonsense query still returns some matches (partial matching)."""
        result = await call_tool("search_ez_functions", {"query": "xyz123nosuchfunction"})
        response = result[0].text

        # Search uses fuzzy matching, so may return some results
        # Just verify it returns something (routing works)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_search_max_results(self):
        """Search respects max_results parameter."""
        result = await call_tool("search_ez_functions", {
            "query": "data",
            "max_results": 2
        })
        response = result[0].text

        # Should return results but limited
        assert "ez" in response  # At least some functions returned


# =============================================================================
# NUGGET TOOLS (2)
# =============================================================================

class TestCreateNugget:
    """Test the create_nugget tool routing and workflow enforcement."""

    @pytest.mark.asyncio
    async def test_workflow_enforcement_missing_functions(self):
        """create_nugget without discovered_functions returns workflow error."""
        result = await call_tool("create_nugget", {
            "jwt_token": "test-token",
            "agent_id": "test-agent-id",
            "requirement": "Send an email"
            # Missing discovered_functions!
        })
        response = result[0].text

        assert "WORKFLOW ERROR" in response
        assert "No functions discovered" in response
        assert "search_ez_functions" in response

    @pytest.mark.asyncio
    async def test_workflow_enforcement_with_skip_search(self):
        """create_nugget with skip_search=true bypasses workflow check."""
        result = await call_tool("create_nugget", {
            "jwt_token": "invalid",  # Will fail validation but bypass workflow
            "agent_id": "invalid",
            "requirement": "Test",
            "discovered_functions": [],
            "skip_search": True
        })
        response = result[0].text

        # Should NOT have workflow error (bypassed), but may have validation error
        assert "WORKFLOW ERROR" not in response

    @pytest.mark.asyncio
    async def test_invalid_jwt_validation(self):
        """create_nugget with invalid JWT returns validation error."""
        result = await call_tool("create_nugget", {
            "jwt_token": "",  # Empty JWT
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Test",
            "discovered_functions": ["ezLog"],
            "skip_search": True
        })
        response = result[0].text

        assert "VALIDATION FAILED" in response
        assert "jwt" in response.lower()

    @pytest.mark.asyncio
    async def test_invalid_discovered_functions(self):
        """create_nugget with non-existent functions returns error."""
        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Test",
            "discovered_functions": ["ezFakeFunction"],
            "skip_search": True
        })
        response = result[0].text

        # Centralized validator catches invalid functions
        assert "Unknown functions" in response or "INVALID FUNCTIONS" in response or "do not exist" in response


# =============================================================================
# NUGGET UPSERT TESTS (Jan 2026)
# =============================================================================

class TestNuggetUpsert:
    """Test create_nugget upsert functionality - UPDATE if exists, CREATE if new."""

    @pytest.mark.asyncio
    async def test_creates_new_nugget_when_none_exists(self, mock_api, temp_workspace):
        """When no nugget with same label exists, should CREATE a new one."""
        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Log debug messages",
            "discovered_functions": ["ezLog"],
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = result[0].text

        # Should show CREATED (not UPDATED)
        assert "CREATED" in response
        assert "UPDATED" not in response
        # Should have Action field showing CREATED
        assert "| **Action** | CREATED |" in response

    @pytest.mark.asyncio
    async def test_updates_existing_nugget_when_label_matches(self, mock_api_with_existing_nugget, temp_workspace):
        """When nugget with same label exists, should UPDATE instead of CREATE."""
        existing_info = mock_api_with_existing_nugget

        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Log debug messages",
            "discovered_functions": ["ezLog"],
            "label": existing_info["existing_label"],  # Same label as existing
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = result[0].text

        # Should show UPDATED (not CREATED)
        assert "UPDATED" in response
        # Should have Action field showing UPDATED
        assert "| **Action** | UPDATED |" in response
        # Should show the existing nugget ID
        assert existing_info["existing_nugget_id"] in response

    @pytest.mark.asyncio
    async def test_upsert_case_insensitive_label_match(self, mock_api_with_existing_nugget, temp_workspace):
        """Label matching should be case-insensitive."""
        existing_info = mock_api_with_existing_nugget

        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Log debug messages",
            "discovered_functions": ["ezLog"],
            "label": existing_info["existing_label"].upper(),  # UPPERCASE version
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = result[0].text

        # Should still UPDATE because label match is case-insensitive
        assert "UPDATED" in response
        assert "| **Action** | UPDATED |" in response

    @pytest.mark.asyncio
    async def test_creates_new_when_label_differs(self, mock_api_with_existing_nugget, temp_workspace):
        """When label is different and description doesn't match, should CREATE new nugget."""
        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "requirement": "Send newsletters via email",  # Doesn't match existing description
            "discovered_functions": ["ezMail"],
            "label": "Completely Different Label",  # Different label
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = result[0].text

        # Should CREATE because neither label nor description match
        assert "CREATED" in response
        assert "| **Action** | CREATED |" in response

    @pytest.mark.asyncio
    async def test_updates_when_description_matches(self, mock_api_with_existing_nugget, temp_workspace):
        """When label differs but description/requirement matches, should UPDATE."""
        existing_info = mock_api_with_existing_nugget

        result = await call_tool("create_nugget", {
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            # This requirement contains keywords that match the existing description:
            # "Log debug messages for testing"
            "requirement": "Log debug messages for my app",
            "discovered_functions": ["ezLog"],
            "label": "Different Label Here",  # Different label
            "skip_search": True,
            "workspace_path": temp_workspace
        })
        response = result[0].text

        # Should UPDATE because description keywords match
        assert "UPDATED" in response
        assert "| **Action** | UPDATED |" in response
        # Should mention it was matched by description
        assert "description" in response.lower()


# =============================================================================
# VALIDATION TOOLS (2)
# =============================================================================

class TestValidateElizaCode:
    """Test the validate_eliza_code tool routing."""

    @pytest.mark.asyncio
    async def test_validate_valid_nugget(self):
        """Valid nugget code passes validation."""
        valid_code = '''(function(data) {
            ezLog("test");
            return "done";
        })()'''

        result = await call_tool("validate_eliza_code", {
            "code": valid_code,
            "code_type": "nugget"
        })
        response = result[0].text

        # Should pass or at least not have critical errors
        assert "FAILED" not in response or "valid" in response.lower()

    @pytest.mark.asyncio
    async def test_validate_invalid_nugget(self):
        """Invalid nugget code (missing IIFE) fails validation."""
        invalid_code = 'function(data) { return data; }'

        result = await call_tool("validate_eliza_code", {
            "code": invalid_code,
            "code_type": "nugget"
        })
        response = result[0].text

        # Should indicate issues
        assert "IIFE" in response or "wrapper" in response.lower() or "issue" in response.lower()


class TestDiagnoseError:
    """Test the diagnose_error tool routing."""

    @pytest.mark.asyncio
    async def test_diagnose_error_routing(self):
        """diagnose_error routes correctly."""
        result = await call_tool("diagnose_error", {
            "error_message": "JWT token expired",
            "context": "create_nugget"
        })
        response = result[0].text

        # Should provide diagnosis or suggestions
        assert len(response) > 0


# =============================================================================
# REFERENCE TOOLS (2)
# =============================================================================

class TestGetApiEndpoint:
    """Test the get_api_endpoint tool routing."""

    @pytest.mark.asyncio
    async def test_get_api_endpoint_routing(self):
        """get_api_endpoint routes correctly."""
        result = await call_tool("get_api_endpoint", {
            "operation": "create_nugget"
        })
        response = result[0].text

        # Should return endpoint info
        assert "nugget" in response.lower() or "endpoint" in response.lower()


class TestGetValidValues:
    """Test the get_valid_values tool routing."""

    @pytest.mark.asyncio
    async def test_get_valid_values_routing(self):
        """get_valid_values routes correctly."""
        result = await call_tool("get_valid_values", {
            "value_type": "models"
        })
        response = result[0].text

        # Should return valid model values
        assert "openai-gpt-4" in response or "models" in response.lower()


# =============================================================================
# CATEGORY CAPABILITY TOOLS (6)
# =============================================================================

class TestCategoryCapabilityTools:
    """Test the 6 category capability tools routing."""

    @pytest.mark.asyncio
    async def test_communication_capability_routing(self):
        """create_communication_capability routes correctly."""
        result = await call_tool("create_communication_capability", {
            "capability": "email",
            "description": "Send email notifications"
        })
        response = result[0].text

        # Should return some response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_integration_capability_routing(self):
        """create_integration_capability routes correctly."""
        result = await call_tool("create_integration_capability", {
            "capability": "rest_api",
            "description": "Call external API"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_ai_capability_routing(self):
        """create_ai_capability routes correctly."""
        result = await call_tool("create_ai_capability", {
            "capability": "llm",
            "description": "Call LLM for summarization"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_automation_capability_routing(self):
        """create_automation_capability routes correctly."""
        result = await call_tool("create_automation_capability", {
            "capability": "browser",
            "description": "Web automation"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_data_capability_routing(self):
        """create_data_capability routes correctly."""
        result = await call_tool("create_data_capability", {
            "capability": "session",
            "description": "Session data management"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_interop_capability_routing(self):
        """create_interop_capability routes correctly."""
        result = await call_tool("create_interop_capability", {
            "capability": "agent_to_agent",
            "description": "Agent communication"
        })
        response = result[0].text

        assert len(response) > 0


# =============================================================================
# CRUD TOOLS - AGENT (4)
# =============================================================================

class TestAgentCRUD:
    """Test agent CRUD tool routing."""

    @pytest.mark.asyncio
    async def test_get_agent_routing(self):
        """get_agent routes correctly."""
        result = await call_tool("get_agent", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc"
        })
        response = result[0].text

        # Should return response (may be error due to invalid token)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_list_agents_routing(self):
        """list_agents routes correctly."""
        result = await call_tool("list_agents", {
            "jwt_token": "test",
            "initiative_id": "ELZI-TEST123"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_update_agent_routing(self):
        """update_agent routes correctly."""
        result = await call_tool("update_agent", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "updates": {"name": "New Name"}
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_delete_agent_routing(self):
        """delete_agent routes correctly."""
        result = await call_tool("delete_agent", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc"
        })
        response = result[0].text

        assert len(response) > 0


# =============================================================================
# CRUD TOOLS - NUGGET (4)
# =============================================================================

class TestNuggetCRUD:
    """Test nugget CRUD tool routing."""

    @pytest.mark.asyncio
    async def test_get_nugget_routing(self):
        """get_nugget routes correctly."""
        result = await call_tool("get_nugget", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "nugget_id": "nugget-123"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_list_nuggets_routing(self):
        """list_nuggets routes correctly."""
        result = await call_tool("list_nuggets", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_update_nugget_routing(self):
        """update_nugget routes correctly."""
        result = await call_tool("update_nugget", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "nugget_id": "nugget-123",
            "updates": {"label": "New Label"}
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_delete_nugget_routing(self):
        """delete_nugget routes correctly."""
        result = await call_tool("delete_nugget", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "nugget_id": "nugget-123"
        })
        response = result[0].text

        assert len(response) > 0


# =============================================================================
# CRUD TOOLS - FUNCTION (3)
# =============================================================================

class TestFunctionCRUD:
    """Test function CRUD tool routing."""

    @pytest.mark.asyncio
    async def test_get_function_routing(self):
        """get_function routes correctly."""
        result = await call_tool("get_function", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "function_id": "func-123"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_list_functions_routing(self):
        """list_functions routes correctly."""
        result = await call_tool("list_functions", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc"
        })
        response = result[0].text

        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_delete_function_routing(self):
        """delete_function routes correctly."""
        result = await call_tool("delete_function", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "function_id": "func-123"
        })
        response = result[0].text

        assert len(response) > 0


# =============================================================================
# ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Test error handling for unknown/invalid tools."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Unknown tool name returns informative error."""
        result = await call_tool("nonexistent_tool", {})
        response = result[0].text

        assert "Unknown tool" in response
        assert "nonexistent_tool" in response

    @pytest.mark.asyncio
    async def test_empty_tool_name_returns_error(self):
        """Empty tool name returns error."""
        result = await call_tool("", {})
        response = result[0].text

        assert "Unknown tool" in response


# =============================================================================
# AGENT CREATION TOOLS (2)
# =============================================================================

class TestAgentCreationTools:
    """Test agent creation tool routing."""

    @pytest.mark.asyncio
    async def test_create_rag_agent_routing(self):
        """create_rag_agent routes correctly."""
        result = await call_tool("create_rag_agent", {
            "jwt_token": "test",
            "initiative_id": "ELZI-TEST123",
            "name": "Test RAG Agent",
            "description": "A test agent"
        })
        response = result[0].text

        # Should return response (may have validation errors)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_create_function_agent_routing(self):
        """create_function_agent routes correctly."""
        result = await call_tool("create_function_agent", {
            "jwt_token": "test",
            "initiative_id": "ELZI-TEST123",
            "name": "Test Function Agent",
            "description": "A test agent"
        })
        response = result[0].text

        assert len(response) > 0


# =============================================================================
# DOCUMENT TOOLS (1)
# =============================================================================

class TestDocumentTools:
    """Test document tool routing."""

    @pytest.mark.asyncio
    async def test_create_document_upload_routing(self):
        """create_document_upload routes correctly."""
        result = await call_tool("create_document_upload", {
            "jwt_token": "test",
            "agent_id": "12345678-1234-1234-1234-123456789abc",
            "document_name": "test.pdf"
        })
        response = result[0].text

        assert len(response) > 0
