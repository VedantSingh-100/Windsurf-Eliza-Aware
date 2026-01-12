"""
Pytest Configuration and Fixtures

Provides shared fixtures for testing:
- Mock JWT tokens
- Mock agent IDs
- Mock API responses
- Test nugget code samples
"""

import pytest
import json
import os
from unittest.mock import MagicMock, patch
from typing import Dict, Any


# =============================================================================
# MOCK DATA FIXTURES
# =============================================================================

@pytest.fixture
def valid_jwt_token():
    """A valid-format JWT token for testing (not a real token)."""
    # Format: header.payload.signature (all base64)
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IlRlc3QgVXNlciIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


@pytest.fixture
def invalid_jwt_tokens():
    """Various invalid JWT tokens for testing validation."""
    return [
        "",  # Empty
        "not-a-jwt",  # No dots
        "only.two.parts",  # Invalid base64
        "{YOUR_JWT}",  # Placeholder
        "jwt_token",  # Placeholder
    ]


@pytest.fixture
def valid_agent_id():
    """A valid UUID format agent ID."""
    return "12345678-1234-1234-1234-123456789abc"


@pytest.fixture
def invalid_agent_ids():
    """Various invalid agent IDs for testing validation."""
    return [
        "",  # Empty
        "not-a-uuid",  # Not UUID format
        "12345678-1234-1234-1234",  # Incomplete
        "{AGENT_ID}",  # Placeholder
        "agent_id",  # Placeholder
    ]


@pytest.fixture
def valid_initiative_id():
    """A valid initiative ID."""
    return "ELZI-XFMLC5G"


@pytest.fixture
def invalid_initiative_ids():
    """Various invalid initiative IDs."""
    return [
        "",  # Empty
        "ELZ-00000",  # Default/placeholder
        "WRONG-12345",  # Wrong prefix
        "ELZI-",  # No user ID
    ]


@pytest.fixture
def valid_nugget_code():
    """Valid nugget JavaScript code."""
    return '''(function(data) {
    var query = data.query || "test";
    ezLog("Searching for: " + query);
    var results = ezInternetSearch(query);
    return "Results: " + results;
})'''


@pytest.fixture
def invalid_nugget_code():
    """Invalid nugget code samples with their expected errors."""
    return [
        {
            "code": "function(data) { return data; }",
            "error": "Missing IIFE wrapper"
        },
        {
            "code": "(function(data) { ezMail('test'); })",
            "error": "ezMail requires JSON.stringify"
        },
        {
            "code": "(function(data) { return data })",  # Missing semicolon is OK in JS
            "error": None  # This should pass
        },
    ]


@pytest.fixture
def valid_discovered_functions():
    """Valid ez* function names."""
    return ["ezMail", "ezInternetSearch", "ezChatCompletions"]


@pytest.fixture
def invalid_discovered_functions():
    """Invalid/non-existent function names."""
    return ["ezFakeFunction", "notAFunction", "ezDoesNotExist"]


# =============================================================================
# MOCK API FIXTURES
# =============================================================================

@pytest.fixture
def mock_api_success_response():
    """Mock successful API response."""
    return {
        "success": True,
        "agentNuggetId": "nugget-12345",
        "agentFunctionId": "func-12345",
    }


@pytest.fixture
def mock_api_error_responses():
    """Mock API error responses by status code."""
    return {
        401: {"error": "Unauthorized", "message": "JWT token expired"},
        403: {"error": "Forbidden", "message": "No access to this resource"},
        404: {"error": "Not Found", "message": "Agent not found"},
        429: {"error": "Rate Limited", "message": "Too many requests"},
        500: {"error": "Server Error", "message": "Internal server error"},
    }


@pytest.fixture
def mock_eliza_client(valid_jwt_token, valid_agent_id, mock_api_success_response):
    """Mock ElizaClient that returns success responses."""
    with patch('eliza_mcp.api.client.ElizaClient') as MockClient:
        instance = MockClient.return_value

        # Mock all methods to return (True, success_response)
        instance.create_agent.return_value = (True, {"agentId": valid_agent_id})
        instance.get_agent.return_value = (True, {"agentId": valid_agent_id, "name": "Test Agent"})
        instance.create_nugget.return_value = (True, mock_api_success_response)
        instance.call_nugget.return_value = (True, {"result": "Test passed"})
        instance.add_function.return_value = (True, {"agentFunctionId": "func-12345"})

        yield instance


# =============================================================================
# HOOK PAYLOAD FIXTURES
# =============================================================================

@pytest.fixture
def pre_write_hook_payload(valid_nugget_code):
    """Payload that Windsurf sends to pre_write_code hook."""
    return {
        "hook": {
            "type": "pre_write_code"
        },
        "file_path": "/workspace/nuggets/test.nugget.js",
        "edits": [
            {
                "type": "insert",
                "start_line": 0,
                "content": valid_nugget_code
            }
        ]
    }


@pytest.fixture
def post_write_hook_payload():
    """Payload that Windsurf sends to post_write_code hook."""
    return {
        "hook": {
            "type": "post_write_code"
        },
        "tool_info": {
            "tool_name": "write_to_file"
        },
        "changed_files": [
            "/workspace/nuggets/test.nugget.js"
        ]
    }


# =============================================================================
# TEST HELPERS
# =============================================================================

@pytest.fixture
def create_temp_nugget_file(tmp_path, valid_nugget_code):
    """Factory fixture to create temporary nugget files."""
    def _create(filename="test.nugget.js", code=None):
        file_path = tmp_path / filename
        file_path.write_text(code or valid_nugget_code)
        return str(file_path)
    return _create


@pytest.fixture
def create_temp_env_file(tmp_path, valid_jwt_token, valid_agent_id):
    """Factory fixture to create temporary .env files."""
    def _create(jwt=None, agent_id=None, env="QA"):
        env_path = tmp_path / ".env"
        content = f"""ELIZA_JWT_TOKEN={jwt or valid_jwt_token}
ELIZA_AGENT_ID={agent_id or valid_agent_id}
ELIZA_ENV={env}
"""
        env_path.write_text(content)
        return str(env_path)
    return _create


# =============================================================================
# FLOW TESTING FIXTURES (Added Jan 2026)
# =============================================================================

@pytest.fixture
def mcp_client():
    """MCP test client for calling tools directly."""
    from tests.helpers.mcp_test_client import MCPTestClient
    return MCPTestClient()


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Temporary workspace directory for file write tests.

    Creates a realistic workspace structure:
    - /workspace/nuggets/{agent_id}/
    - /workspace/.env
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "nuggets").mkdir()
    return str(workspace)


@pytest.fixture
def hook_runner():
    """Hook runner for simulating Windsurf hook execution."""
    from tests.helpers.hook_runner import run_hook, run_hook_on_file, create_hook_payload
    return type('HookRunner', (), {
        'run': staticmethod(run_hook),
        'run_on_file': staticmethod(run_hook_on_file),
        'create_payload': staticmethod(create_hook_payload)
    })()


class MockResponse:
    """Mock response for requests library."""

    def __init__(self, status_code: int, json_data: dict, text: str = None):
        self.status_code = status_code
        self._json = json_data
        self.text = text or json.dumps(json_data)

    def json(self):
        return self._json


@pytest.fixture
def mock_api(monkeypatch):
    """
    Mock all Eliza API calls for fast, offline testing.

    Mocks requests.post, requests.get, requests.delete to simulate
    the Eliza CogEngine API responses.
    """

    def mock_post(url, **kwargs):
        """Mock POST requests."""
        if "/nuggets/list" in url:
            # List nuggets - return empty by default
            # Tests can override this via monkeypatch for upsert testing
            return MockResponse(200, {
                "data": [],
                "total": 0
            })
        elif "/nuggets/" in url and "/call" not in url:
            # Create nugget
            return MockResponse(200, {
                "agentNuggetId": "test-nugget-id-12345",
                "label": "Test Nugget",
                "status": "active"
            })
        elif "/call" in url:
            # Execute nugget (runtime validation)
            return MockResponse(200, {
                "result": "Execution successful",
                "data": {"query": "test"}
            })
        elif "/functions" in url:
            # Create function
            return MockResponse(200, {
                "agentFunctionId": "test-func-id-12345",
                "funcNameKey": "test_function"
            })
        elif "/agents/" in url and "/nuggets" not in url and "/functions" not in url:
            # Create agent
            return MockResponse(200, {
                "agentId": "test-agent-id-12345",
                "name": "Test Agent"
            })
        return MockResponse(404, {"error": "not found"})

    def mock_get(url, **kwargs):
        """Mock GET requests."""
        if "/agents/" in url:
            if "/nuggets/" in url:
                # Get nugget
                return MockResponse(200, {
                    "agentNuggetId": "test-nugget-id",
                    "label": "Test Nugget"
                })
            elif "/functions/" in url:
                # Get function
                return MockResponse(200, {
                    "agentFunctionId": "test-func-id",
                    "funcNameKey": "test_function"
                })
            else:
                # Get agent
                return MockResponse(200, {
                    "agentId": "test-agent-id",
                    "name": "Test Agent"
                })
        return MockResponse(404, {"error": "not found"})

    def mock_delete(url, **kwargs):
        """Mock DELETE requests."""
        return MockResponse(200, {"deleted": True})

    def mock_put(url, **kwargs):
        """Mock PUT requests."""
        if "/nuggets/" in url:
            # Update nugget - extract nugget ID from URL
            nugget_id = url.split("/nuggets/")[-1].rstrip("/")
            return MockResponse(200, {
                "agentNuggetId": nugget_id,
                "label": "Updated Nugget",
                "status": "active",
                "updated": True
            })
        return MockResponse(200, {"updated": True})

    monkeypatch.setattr("requests.post", mock_post)
    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.delete", mock_delete)
    monkeypatch.setattr("requests.put", mock_put)


@pytest.fixture
def mock_api_errors(monkeypatch):
    """
    Mock API to return error responses.

    Useful for testing error handling paths.
    """

    def mock_post_error(url, **kwargs):
        """Mock POST to return 401 Unauthorized."""
        return MockResponse(401, {
            "error": "Unauthorized",
            "message": "JWT token expired or invalid"
        })

    def mock_get_error(url, **kwargs):
        """Mock GET to return 404 Not Found."""
        return MockResponse(404, {
            "error": "Not Found",
            "message": "Resource not found"
        })

    monkeypatch.setattr("requests.post", mock_post_error)
    monkeypatch.setattr("requests.get", mock_get_error)


@pytest.fixture
def mock_api_with_existing_nugget(monkeypatch):
    """
    Mock API that returns an existing nugget in the list.

    Used for testing upsert functionality - when a nugget with the
    same label already exists, create_nugget should UPDATE instead of CREATE.
    """
    existing_nugget_id = "existing-nugget-id-99999"
    existing_label = "Test Nugget"  # This matches what codegen generates for ezLog
    existing_description = "Log debug messages for testing"
    existing_prompt = "Use this nugget to log messages"

    def mock_post(url, **kwargs):
        """Mock POST requests with existing nugget in list."""
        if "/nuggets/list" in url:
            # Return existing nugget with all fields
            return MockResponse(200, {
                "data": [
                    {
                        "agentNuggetId": existing_nugget_id,
                        "label": existing_label,
                        "description": existing_description,
                        "prompt": existing_prompt,
                        "status": "active"
                    }
                ],
                "total": 1
            })
        elif "/nuggets/" in url and "/call" not in url:
            # Create nugget (shouldn't be called when updating)
            return MockResponse(200, {
                "agentNuggetId": "new-nugget-id-12345",
                "label": "New Nugget",
                "status": "active"
            })
        elif "/call" in url:
            # Execute nugget (runtime validation)
            return MockResponse(200, {
                "result": "Execution successful",
                "data": {"query": "test"}
            })
        elif "/functions" in url:
            # Create function
            return MockResponse(200, {
                "agentFunctionId": "test-func-id-12345",
                "funcNameKey": "test_function"
            })
        return MockResponse(404, {"error": "not found"})

    def mock_put(url, **kwargs):
        """Mock PUT requests for update."""
        if "/nuggets/" in url:
            return MockResponse(200, {
                "agentNuggetId": existing_nugget_id,
                "label": existing_label,
                "status": "active",
                "updated": True
            })
        return MockResponse(200, {"updated": True})

    def mock_get(url, **kwargs):
        """Mock GET requests."""
        return MockResponse(200, {"agentId": "test-agent"})

    def mock_delete(url, **kwargs):
        """Mock DELETE requests."""
        return MockResponse(200, {"deleted": True})

    monkeypatch.setattr("requests.post", mock_post)
    monkeypatch.setattr("requests.put", mock_put)
    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.delete", mock_delete)

    return {
        "existing_nugget_id": existing_nugget_id,
        "existing_label": existing_label,
        "existing_description": existing_description,
        "existing_prompt": existing_prompt
    }


# =============================================================================
# NUGGET FILE FIXTURES
# =============================================================================

@pytest.fixture
def valid_nugget_file(tmp_path, valid_nugget_code):
    """Create a valid nugget file for hook testing."""
    nugget_dir = tmp_path / "nuggets"
    nugget_dir.mkdir()
    nugget_file = nugget_dir / "test.nugget.js"
    nugget_file.write_text(valid_nugget_code)
    return str(nugget_file)


@pytest.fixture
def invalid_nugget_file(tmp_path):
    """Create an invalid nugget file (missing IIFE wrapper)."""
    nugget_dir = tmp_path / "nuggets"
    nugget_dir.mkdir()
    nugget_file = nugget_dir / "invalid.nugget.js"
    # Missing IIFE wrapper - should fail static validation
    nugget_file.write_text('function(data) { ezLog("test"); }')
    return str(nugget_file)


@pytest.fixture
def ezmail_nugget_file(tmp_path):
    """Create a nugget file with ezMail (requires JSON.stringify check)."""
    nugget_dir = tmp_path / "nuggets"
    nugget_dir.mkdir()
    nugget_file = nugget_dir / "email.nugget.js"
    # This should fail because ezMail needs JSON.stringify
    nugget_file.write_text('''(function(data) {
    ezMail(data.email, "Subject", "Body");
    return "sent";
})()''')
    return str(nugget_file)


@pytest.fixture
def valid_ezmail_nugget_file(tmp_path):
    """Create a valid nugget file with ezMail and JSON.stringify."""
    nugget_dir = tmp_path / "nuggets"
    nugget_dir.mkdir()
    nugget_file = nugget_dir / "valid_email.nugget.js"
    nugget_file.write_text('''(function(data) {
    var result = ezMail(data.email, "Subject", "Body");
    return JSON.stringify(result);
})()''')
    return str(nugget_file)


@pytest.fixture
def non_nugget_file():
    """
    Create a regular JS file (not a nugget).

    Note: Must be in a path that doesn't match nugget patterns:
    - No 'nugget' in path
    - Not in a 'nuggets' directory

    Uses a custom temp directory to avoid pytest test names with 'nugget'.
    """
    import tempfile
    import shutil

    # Create temp dir with explicit name (no 'nugget' anywhere)
    temp_dir = tempfile.mkdtemp(prefix="eliza_test_scripts_")
    js_file = os.path.join(temp_dir, "utils.js")

    with open(js_file, 'w') as f:
        f.write('console.log("hello");')

    yield js_file

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
