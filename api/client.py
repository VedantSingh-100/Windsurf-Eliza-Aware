"""
Eliza API Client

HTTP client for interacting with Eliza CogEngine API.

RESPONSE HANDLING:
- Success: 200, 201, 204
- Errors: 401 (auth), 403 (permission), 404 (not found), 429 (rate limit), 5xx (server)
- Exceptions: Timeout, ConnectionError, JSONDecodeError
"""

import json
import requests
import urllib3
from typing import Dict, Any, Optional, Tuple

# Disable SSL warnings for internal certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CogEngine base URLs by environment
COGENGINE_URLS = {
    "DEV": "https://cognitive-engine-personal.dev.bny.net/cog",
    "TEST": "https://cognitive-engine-personal.test.bny.net/cog",
    "QA": "https://cognitive-engine-personal.qa.bny.net/cog",
    "PROD": "https://cognitive-engine-personal.bny.net/cog"
}

# Success HTTP status codes
SUCCESS_CODES = {200, 201, 204}


class ElizaClient:
    """HTTP client for Eliza CogEngine API."""

    def __init__(self, jwt_token: str, env: str = "QA"):
        self.jwt_token = jwt_token
        self.env = env.upper() if env else "QA"
        self.base_url = COGENGINE_URLS.get(self.env, COGENGINE_URLS["QA"])
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "x-jwt-assertion": jwt_token,
            "REQUESTER-ID": "MCP_SERVER"
        }

    def _request(self, method: str, path: str, data: Dict = None, timeout: int = 30) -> Tuple[bool, Dict[str, Any]]:
        """
        Make HTTP request to Eliza API.

        Returns:
            Tuple[bool, Dict]: (success, response_or_error)
            - success=True: response contains API data
            - success=False: response contains 'error', 'details', and 'fix' keys

        Response handling:
        - 200: Parse JSON body
        - 201: {"success": True, "created": True} + parsed body
        - 204: {"success": True}
        - 401: JWT expired/invalid
        - 403: Permission denied
        - 404: Resource not found
        - 429: Rate limited
        - 5xx: Server error
        """
        url = f"{self.base_url}{path}"

        try:
            # Make the request
            if method == "GET":
                resp = requests.get(url, headers=self.headers, verify=False, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=self.headers, verify=False, timeout=timeout)
            elif method == "PUT":
                resp = requests.put(url, json=data, headers=self.headers, verify=False, timeout=timeout)
            elif method == "PATCH":
                resp = requests.patch(url, json=data, headers=self.headers, verify=False, timeout=timeout)
            elif method == "DELETE":
                resp = requests.delete(url, headers=self.headers, verify=False, timeout=timeout)
            else:
                return False, {"error": f"Unknown HTTP method: {method}", "fix": "Use GET, POST, PUT, PATCH, or DELETE"}

            # Handle success responses
            if resp.status_code in SUCCESS_CODES:
                if resp.status_code == 204:
                    return True, {"success": True}

                # Try to parse JSON response
                try:
                    response_data = resp.json() if resp.text else {"success": True}
                except json.JSONDecodeError:
                    response_data = {"success": True, "raw_response": resp.text}

                if resp.status_code == 201:
                    response_data["created"] = True

                return True, response_data

            # Handle error responses with actionable messages
            error_response = self._handle_error_response(resp)
            return False, error_response

        except requests.exceptions.Timeout:
            return False, {
                "error": "Request timed out",
                "details": f"Request to {path} exceeded {timeout}s timeout",
                "fix": "Increase timeout or retry the request"
            }

        except requests.exceptions.ConnectionError as e:
            return False, {
                "error": "Connection failed",
                "details": str(e),
                "fix": "Check VPN connection and network access to CogEngine"
            }

        except json.JSONDecodeError as e:
            return False, {
                "error": "Invalid JSON response",
                "details": str(e),
                "fix": "The API returned invalid JSON - this may be a server issue"
            }

        except Exception as e:
            return False, {
                "error": "Unexpected error",
                "details": str(e),
                "fix": "Check the error details and retry"
            }

    def _handle_error_response(self, resp: requests.Response) -> Dict[str, Any]:
        """Convert HTTP error response to actionable error dict."""
        status = resp.status_code

        # Try to extract error details from response body
        try:
            error_body = resp.json() if resp.text else {}
        except json.JSONDecodeError:
            error_body = {"raw": resp.text[:500] if resp.text else ""}

        # Map status codes to actionable error messages
        if status == 401:
            return {
                "error": "Authentication failed (401)",
                "details": error_body,
                "fix": "JWT token is expired or invalid. Get a fresh token from Eliza UI."
            }

        elif status == 403:
            return {
                "error": "Permission denied (403)",
                "details": error_body,
                "fix": "You don't have permission for this resource. Check initiative_id and agent ownership."
            }

        elif status == 404:
            return {
                "error": "Resource not found (404)",
                "details": error_body,
                "fix": "Verify the agent_id, nugget_id, or function_id exists and is correct."
            }

        elif status == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            return {
                "error": "Rate limited (429)",
                "details": error_body,
                "fix": f"Too many requests. Wait {retry_after} seconds before retrying."
            }

        elif status == 400:
            return {
                "error": "Bad request (400)",
                "details": error_body,
                "fix": "Check request parameters and data format."
            }

        elif status == 409:
            return {
                "error": "Conflict (409)",
                "details": error_body,
                "fix": "Resource already exists or there's a version conflict."
            }

        elif status == 422:
            return {
                "error": "Validation failed (422)",
                "details": error_body,
                "fix": "Request data failed server validation. Check field values."
            }

        elif 500 <= status < 600:
            return {
                "error": f"Server error ({status})",
                "details": error_body,
                "fix": "CogEngine server error. Wait a moment and retry. If persistent, contact Eliza support."
            }

        else:
            return {
                "error": f"HTTP {status}",
                "details": error_body,
                "fix": "Unexpected error. Check details and retry."
            }

    # Legacy method for backwards compatibility
    def _request_legacy(self, method: str, path: str, data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """Legacy request method for backwards compatibility."""
        success, result = self._request(method, path, data, timeout)
        if success:
            return result
        else:
            return {"error": result.get("error", "Unknown error"), "details": result.get("details", "")}

    # =========================================================================
    # AGENT OPERATIONS
    # =========================================================================

    def create_agent(self, agent_data: Dict) -> Tuple[bool, Dict]:
        """Create a new agent."""
        return self._request("POST", "/agents", agent_data)

    def get_agent(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get agent by ID."""
        return self._request("GET", f"/agents/{agent_id}")

    def update_agent(self, agent_id: str, updates: Dict) -> Tuple[bool, Dict]:
        """
        Update agent configuration.

        Updates can include:
        - name: Agent display name
        - description: Agent description
        - systemPrompt: System prompt
        - model: LLM model name
        - controlFlags: List of control flags
        - retrieverStrategy: RAG strategy
        """
        return self._request("PUT", f"/agents/{agent_id}", updates)

    def delete_agent(self, agent_id: str) -> Tuple[bool, Dict]:
        """Delete agent."""
        return self._request("DELETE", f"/agents/{agent_id}")

    def list_agents(self, offset: int = 0, limit: int = 20) -> Tuple[bool, Dict]:
        """List agents for the current user."""
        return self._request("POST", "/agents/list", {"offset": offset, "limit": limit})

    # =========================================================================
    # NUGGET OPERATIONS
    # =========================================================================

    def create_nugget(self, agent_id: str, nugget_data: Dict) -> Tuple[bool, Dict]:
        """Create a nugget on an agent."""
        return self._request("POST", f"/agents/{agent_id}/nuggets/", nugget_data)

    def get_nugget(self, agent_id: str, nugget_id: str) -> Tuple[bool, Dict]:
        """Get nugget details by ID."""
        return self._request("GET", f"/agents/{agent_id}/nuggets/{nugget_id}")

    def update_nugget(self, agent_id: str, nugget_id: str, updates: Dict) -> Tuple[bool, Dict]:
        """
        Update nugget code or configuration.

        Updates can include:
        - label: Nugget display name
        - description: What the nugget does
        - call: Code block with @type, language, and code
        """
        return self._request("PUT", f"/agents/{agent_id}/nuggets/{nugget_id}", updates)

    def delete_nugget(self, agent_id: str, nugget_id: str) -> Tuple[bool, Dict]:
        """Delete a nugget from an agent."""
        return self._request("DELETE", f"/agents/{agent_id}/nuggets/{nugget_id}")

    def list_nuggets(self, agent_id: str, offset: int = 0, limit: int = 20) -> Tuple[bool, Dict]:
        """List all nuggets on an agent."""
        return self._request("POST", f"/agents/{agent_id}/nuggets/list", {"offset": offset, "limit": limit})

    def search_nuggets(self, agent_id: str, search_data: Dict) -> Tuple[bool, Dict]:
        """Search nuggets on an agent."""
        return self._request("POST", f"/agents/{agent_id}/nuggets/search", search_data)

    def call_nugget(self, agent_id: str, nugget_id: str, data: Dict) -> Tuple[bool, Dict]:
        """Execute a nugget (for validation or testing)."""
        return self._request("POST", f"/agents/{agent_id}/nuggets/{nugget_id}/call", data, timeout=60)

    # =========================================================================
    # FUNCTION OPERATIONS
    # =========================================================================

    def add_function(self, agent_id: str, function_data: Dict) -> Tuple[bool, Dict]:
        """Add a function to an agent."""
        return self._request("POST", f"/agents/{agent_id}/functions", function_data)

    def get_function(self, agent_id: str, function_id: str) -> Tuple[bool, Dict]:
        """Get function details by ID."""
        return self._request("GET", f"/agents/{agent_id}/functions/{function_id}")

    def delete_function(self, agent_id: str, function_id: str) -> Tuple[bool, Dict]:
        """Delete a function from an agent (nugget remains)."""
        return self._request("DELETE", f"/agents/{agent_id}/functions/{function_id}")

    def list_functions(self, agent_id: str) -> Tuple[bool, Dict]:
        """List all functions on an agent."""
        return self._request("GET", f"/agents/{agent_id}/functions")

    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================

    def list_documents(self, agent_id: str, offset: int = 0, limit: int = 10) -> Tuple[bool, Dict]:
        """List documents on an agent."""
        return self._request("POST", f"/agents/{agent_id}/documents", {"offset": offset, "limit": limit})

    def search_documents(self, agent_id: str, content: list) -> Tuple[bool, Dict]:
        """Search documents on an agent."""
        return self._request("POST", f"/agents/{agent_id}/documents/search", {"content": content})

    def delete_document(self, agent_id: str, document_id: str) -> Tuple[bool, Dict]:
        """Delete a document from an agent."""
        return self._request("DELETE", f"/agents/{agent_id}/documents/{document_id}")

    # =========================================================================
    # CHAT OPERATIONS
    # =========================================================================

    def chat(self, agent_id: str, message: str, session_id: str = None) -> Tuple[bool, Dict]:
        """Send chat message to agent."""
        data = {
            "agentId": agent_id,
            "message": message
        }
        if session_id:
            data["sessionId"] = session_id
        return self._request("POST", "/agents/chat", data, timeout=120)

    def query_agent(self, agent_id: str, query: str) -> Tuple[bool, Dict]:
        """Query an agent (alias for chat)."""
        return self.chat(agent_id, query)


def get_client(jwt_token: str, env: str = "QA") -> ElizaClient:
    """Create and return an ElizaClient instance."""
    return ElizaClient(jwt_token, env)