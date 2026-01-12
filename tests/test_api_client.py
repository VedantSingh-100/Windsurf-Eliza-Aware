"""
Tests for API Client

Tests the api/client.py module:
- ElizaClient methods
- Response handling (success/error codes)
- Error messages are actionable
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.client import ElizaClient, get_client, COGENGINE_URLS, SUCCESS_CODES


class TestElizaClientInit:
    """Tests for client initialization."""

    def test_client_sets_base_url(self, valid_jwt_token):
        """Client should set correct base URL for environment."""
        for env in ["DEV", "TEST", "QA", "PROD"]:
            client = ElizaClient(valid_jwt_token, env)
            assert client.base_url == COGENGINE_URLS[env]

    def test_client_sets_headers(self, valid_jwt_token):
        """Client should set required headers."""
        client = ElizaClient(valid_jwt_token, "QA")
        assert "Authorization" in client.headers
        assert "x-jwt-assertion" in client.headers
        assert client.headers["x-jwt-assertion"] == valid_jwt_token

    def test_get_client_factory(self, valid_jwt_token):
        """get_client should return ElizaClient instance."""
        client = get_client(valid_jwt_token, "QA")
        assert isinstance(client, ElizaClient)


class TestResponseHandling:
    """Tests for API response handling."""

    @patch('api.client.requests')
    def test_success_200_returns_json(self, mock_requests, valid_jwt_token, valid_agent_id):
        """HTTP 200 should return parsed JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"agentId": "test-123"}'
        mock_response.json.return_value = {"agentId": "test-123"}
        mock_requests.get.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("GET", "/agents/test")

        assert success is True
        assert result["agentId"] == "test-123"

    @patch('api.client.requests')
    def test_success_201_includes_created_flag(self, mock_requests, valid_jwt_token):
        """HTTP 201 should include created=True."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": "new-123"}'
        mock_response.json.return_value = {"id": "new-123"}
        mock_requests.post.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("POST", "/agents", {})

        assert success is True
        assert result.get("created") is True

    @patch('api.client.requests')
    def test_success_204_returns_success(self, mock_requests, valid_jwt_token):
        """HTTP 204 should return success dict."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_requests.delete.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("DELETE", "/agents/test")

        assert success is True
        assert result.get("success") is True

    @patch('api.client.requests')
    def test_error_401_has_actionable_fix(self, mock_requests, valid_jwt_token):
        """HTTP 401 should include actionable fix message."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "Unauthorized"}'
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_requests.get.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("GET", "/agents/test")

        assert success is False
        assert "fix" in result
        assert "JWT" in result["fix"] or "token" in result["fix"].lower()

    @patch('api.client.requests')
    def test_error_404_has_actionable_fix(self, mock_requests, valid_jwt_token):
        """HTTP 404 should include actionable fix message."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = '{"error": "Not Found"}'
        mock_response.json.return_value = {"error": "Not Found"}
        mock_requests.get.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("GET", "/agents/nonexistent")

        assert success is False
        assert "fix" in result
        assert "agent_id" in result["fix"].lower() or "not found" in result["error"].lower()

    @patch('api.client.requests')
    def test_error_429_includes_retry_info(self, mock_requests, valid_jwt_token):
        """HTTP 429 should include retry information."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = '{"error": "Rate Limited"}'
        mock_response.json.return_value = {"error": "Rate Limited"}
        mock_requests.get.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("GET", "/agents")

        assert success is False
        assert "fix" in result
        assert "60" in result["fix"] or "wait" in result["fix"].lower()


class TestExceptionHandling:
    """Tests for exception handling in requests."""

    @patch('api.client.requests')
    def test_timeout_handled(self, mock_requests, valid_jwt_token):
        """Timeout exception should be handled gracefully."""
        import requests
        mock_requests.get.side_effect = requests.exceptions.Timeout()

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("GET", "/agents/test", timeout=1)

        assert success is False
        assert "timeout" in result["error"].lower()
        assert "fix" in result

    @patch('api.client.requests')
    def test_connection_error_handled(self, mock_requests, valid_jwt_token):
        """Connection error should be handled gracefully."""
        import requests
        mock_requests.get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client._request("GET", "/agents/test")

        assert success is False
        assert "connection" in result["error"].lower()
        assert "fix" in result


class TestClientMethods:
    """Tests for specific client methods."""

    @patch('api.client.requests')
    def test_create_agent(self, mock_requests, valid_jwt_token):
        """create_agent should POST to /agents."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"agentId": "new-agent"}'
        mock_response.json.return_value = {"agentId": "new-agent"}
        mock_requests.post.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client.create_agent({"name": "Test"})

        mock_requests.post.assert_called_once()
        assert "/agents" in str(mock_requests.post.call_args)

    @patch('api.client.requests')
    def test_get_agent(self, mock_requests, valid_jwt_token, valid_agent_id):
        """get_agent should GET /agents/{id}."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"agentId": "test"}'
        mock_response.json.return_value = {"agentId": "test"}
        mock_requests.get.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client.get_agent(valid_agent_id)

        mock_requests.get.assert_called_once()
        assert valid_agent_id in str(mock_requests.get.call_args)

    @patch('api.client.requests')
    def test_create_nugget(self, mock_requests, valid_jwt_token, valid_agent_id):
        """create_nugget should POST to /agents/{id}/nuggets/."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"agentNuggetId": "nugget-123"}'
        mock_response.json.return_value = {"agentNuggetId": "nugget-123"}
        mock_requests.post.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client.create_nugget(valid_agent_id, {"label": "Test"})

        mock_requests.post.assert_called_once()
        assert f"/agents/{valid_agent_id}/nuggets" in str(mock_requests.post.call_args)

    @patch('api.client.requests')
    def test_delete_agent(self, mock_requests, valid_jwt_token, valid_agent_id):
        """delete_agent should DELETE /agents/{id}."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_requests.delete.return_value = mock_response

        client = ElizaClient(valid_jwt_token, "QA")
        success, result = client.delete_agent(valid_agent_id)

        mock_requests.delete.assert_called_once()
        assert valid_agent_id in str(mock_requests.delete.call_args)
