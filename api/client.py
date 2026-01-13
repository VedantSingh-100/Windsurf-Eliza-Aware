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

    def create_agent(self, agent_data: Dict) -> Tuple[bool, Dict]:
        """Create a new agent.

        Args:
            agent_data: AgentCreateVo containing agent configuration.

        Request Body (AgentCreateVo):
            - name: string - Agent Name
            - description: string - Description of agent
            - prompt: string - System prompt for the agent
            - retrieverStrategy: string - Retriever strategy (STANDARD, REASON, etc.)
            - llmModel: string - LLM model name (e.g., openai-gpt-4o)
            - initiativeId: string - Initiative ID (required, format: ELZI-{userid})
            - controlFlags: array[string] - Control flags (ADD_KNOWLEDGE, USE_HISTORY, etc.)
            - agentType: string - Type of agent
            - welcomeMessage: string - Welcome message displayed to user
            - metadata: object - Custom metadata
            - identity: object - Identity configuration
            - isActive: boolean - Toggle to activate/deactivate agent

        Returns:
            Tuple of (success: bool, response: Dict with created agent)

        Responses:
            - 200: Successfully processed
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", "/agents", agent_data)

    def get_agent(self, agent_id: str, include_documents: bool = False) -> Tuple[bool, Dict]:
        """Retrieve an agent by ID.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            include_documents: boolean (optional) - Include documents in response.

        Returns:
            Tuple of (success: bool, response: Dict with agent details)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        url = f"/agents/{agent_id}"
        if include_documents:
            url += "?includeDocuments=true"
        return self._request("GET", url)

    def update_agent(self, agent_id: str, updates: Dict) -> Tuple[bool, Dict]:
        """Update agent attributes.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            updates: AgentCreateVo containing fields to update.

        Request Body (AgentCreateVo):
            - name: string - Agent Name
            - description: string - Description of agent
            - prompt: string - System prompt for the agent
            - retrieverStrategy: string - Retriever strategy (STANDARD, REASON, etc.)
            - llmModel: string - LLM model name
            - controlFlags: array[string] - Control flags
            - welcomeMessage: string - Welcome message
            - metadata: object - Custom metadata
            - isActive: boolean - Toggle to activate/deactivate agent

        Returns:
            Tuple of (success: bool, response: Dict with updated agent)

        Responses:
            - 200: Successfully processed
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("PUT", f"/agents/{agent_id}", updates)

    def delete_agent(self, agent_id: str) -> Tuple[bool, Dict]:
        """Delete an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully deleted
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("DELETE", f"/agents/{agent_id}")

    # ================================================================
    # NUGGET OPERATIONS
    # ================================================================

    def create_nugget(self, agent_id: str, nugget_data: Dict) -> Tuple[bool, Dict]:
        """Create a nugget on an agent.

        Args:
            agent_id: UUID of the agent.
            nugget_data: CognitiveAgentNugget containing:
                - label: Nugget display name
                - description: What the nugget does
                - call: Code block with @type, language, and code
                - prompt: When LLM should use this nugget
                - params: Input parameters array

        Returns:
            Tuple of (success: bool, response: Dict)
        """
        return self._request("POST", f"/agents/{agent_id}/nuggets/", nugget_data)

    def get_nugget(self, agent_id: str, nugget_id: str) -> Tuple[bool, Dict]:
        """Get nugget details by ID.

        Args:
            agent_id: UUID of the agent.
            nugget_id: UUID of the nugget to retrieve.

        Returns:
            Tuple of (success: bool, response: Dict with CognitiveAgentNugget)
        """
        return self._request("GET", f"/agents/{agent_id}/nuggets/{nugget_id}")

    def update_nugget(self, agent_id: str, nugget_id: str, updates: Dict, is_default: bool = None) -> Tuple[bool, Dict]:
        """Update nugget code or configuration.

        Args:
            agent_id: UUID of the agent.
            nugget_id: UUID of the nugget to update.
            updates: Fields to update (label, description, call, prompt, params,
                controlFlags, metadata, status, returnResultDirectly).
            is_default: Optional; make this the default nugget for the agent.

        Returns:
            Tuple of (success: bool, response: Dict)

        Note:
            agentId is automatically included in body to match path parameter.
        """
        # API requires agentId in body to match path parameter
        body = {"agentId": agent_id, **updates}

        # Build URL with optional query param
        url = f"/agents/{agent_id}/nuggets/{nugget_id}"
        if is_default is not None:
            url += f"?isDefault={str(is_default).lower()}"

        return self._request("POST", url, body)

    def delete_nugget(self, agent_id: str, nugget_id: str) -> Tuple[bool, Dict]:
        """Delete a nugget from an agent.

        Args:
            agent_id: UUID of the agent.
            nugget_id: UUID of the nugget to delete.

        Returns:
            Tuple of (success: bool, response: Dict)
        """
        return self._request("DELETE", f"/agents/{agent_id}/nuggets/{nugget_id}")

    def search_nuggets(self, agent_id: str, search_data: Dict) -> Tuple[bool, Dict]:
        """Search nuggets on an agent.

        Args:
            agent_id: UUID of the agent.
            search_data: NuggetSearchRequest containing:
                - historicalSearch: boolean, search historical nuggets
                - nuggetId: string, specific nugget ID to search

        Returns:
            Tuple of (success: bool, response: Dict with NuggetSearchResponse)
        """
        return self._request("POST", f"/agents/{agent_id}/nuggets/search", search_data)

    def call_nugget(self, agent_id: str, nugget_id: str, data: Dict) -> Tuple[bool, Dict]:
        """Execute a nugget by ID.

        Args:
            agent_id: UUID of the agent.
            nugget_id: UUID of the nugget to execute.
            data: NuggetCallRequest containing:
                - data: Key-value pairs for nugget execution
                - sessionId: Optional session identifier
                - requestId: Optional request identifier

        Returns:
            Tuple of (success: bool, response: Dict with NuggetCallResponse)
        """
        return self._request("POST", f"/agents/{agent_id}/nuggets/{nugget_id}/call", data, timeout=60)

    def call_dynamic_nugget(self, agent_id: str, data: Dict) -> Tuple[bool, Dict]:
        """Call a dynamic nugget without specifying nugget ID.

        Args:
            agent_id: UUID of the agent.
            data: NuggetCallRequest containing:
                - data: Key-value pairs for nugget execution
                - sessionId: Optional session identifier
                - requestId: Optional request identifier
                - args: Optional string array of arguments

        Returns:
            Tuple of (success: bool, response: Dict with NuggetCallResponse)
        """
        return self._request("POST", f"/agents/{agent_id}/nuggets/call", data, timeout=60)

    def call_bulk_nuggets(self, agent_id: str, data: Dict) -> Tuple[bool, Dict]:
        """Execute multiple nuggets in bulk.

        Args:
            agent_id: UUID of the agent.
            data: NuggetCallBulkRequest containing:
                - runKey: Identifier for the bulk run
                - data: Key-value pairs for nugget execution
                - nuggetIds: Array of nugget IDs to execute

        Returns:
            Tuple of (success: bool, response: Dict with NuggetCallBulkResponse)
        """
        return self._request("POST", f"/agents/{agent_id}/nuggets/call-bulk", data, timeout=120)

    # ================================================================
    # FUNCTION OPERATIONS
    # ================================================================

    def add_function(self, agent_id: str, function_data: Dict) -> Tuple[bool, Dict]:
        """Create a function on an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            function_data: CognitiveAgentFunctionConfig containing function configuration.

        Request Body (CognitiveAgentFunctionConfig):
            - funcNameKey: string - Function name key (identifier)
            - label: string - Function text displayed to the user
            - prompt: string - Function prompt (when LLM should use this)
            - functionType: enum - Type: SQL, API, REST, PYTHON_STATIC, NUGGET, AGENT, etc.
            - nuggetId: string - Nugget ID (for NUGGET type functions)
            - params: array[object] - Function parameters
            - returnResultDirectly: boolean - Return result without LLM processing
            - code: string - Code (for PYTHON_STATIC type)
            - dataSource: string - Data source name (for SQL type)
            - sql: string - SQL query (for SQL type)
            - httpMethod: string - HTTP method (for REST/API type)
            - path: string - API path (for REST/API type)

        Returns:
            Tuple of (success: bool, response: Dict with created function).

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/functions", function_data)

    def get_function(self, agent_id: str, function_id: str) -> Tuple[bool, Dict]:
        """Get function details by ID.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            function_id: string (required) - Unique ID for the function.

        Returns:
            Tuple of (success: bool, response: Dict with CognitiveAgentFunctionConfig)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/functions/{function_id}")

    def delete_function(self, agent_id: str, document_id: str, function_id: str) -> Tuple[bool, Dict]:
        """Delete a function from an agent.

        Args:
            agent_id: UUID of the agent.
            document_id: UUID of the agent's document.
            function_id: UUID of the function to delete.

        Returns:
            Tuple of (success: bool, response: Dict)

        Note:
            The underlying nugget remains; only the function binding is removed.
        """
        return self._request("DELETE", f"/agents/{agent_id}/documents/{document_id}/functions/{function_id}")

    def list_functions(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get all functions on an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with list of functions)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/functions")

    # ================================================================
    # DOCUMENT OPERATIONS
    # ================================================================

    def list_documents(self, agent_id: str, offset: int = 0, limit: int = 10) -> Tuple[bool, Dict]:
        """Retrieve an agent's documents.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            offset: integer (optional) - Pagination offset. Default: 0.
            limit: integer (optional) - Number of results to return. Default: 10.

        Request Body (CognitiveAgentDocumentListRequestVO):
            - offset: integer - Pagination offset
            - limit: integer - Number of results
            - inclFileTypeList: array[string] - File types to include
            - exclFileTypeList: array[string] - File types to exclude
            - status: array[string] - Document indexing status filter
            - keywords: array[string] - Keywords filter
            - sessionId: string - Session ID

        Returns:
            Tuple of (success: bool, response: Dict with paginated document list)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/documents", {"offset": offset, "limit": limit})

    def search_documents(self, agent_id: str, content: list) -> Tuple[bool, Dict]:
        """Search for documents on an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            content: array[string] (required) - Content search terms.

        Request Body (SearchDocumentRequest):
            - content: array[string] - Content search terms
            - selectColumns: string - Columns to select
            - highlight: string - Highlight fields
            - documentsToReturnCount: integer - Count of documents to return
            - orderby: string - Order by clause
            - chunkType: enum (FULL, PARTIAL) - Chunk type to search
            - fullTextSearch: object - Full text search options
            - paginationOptions: object - Pagination options

        Returns:
            Tuple of (success: bool, response: Dict with search results)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/documents/search", {"content": content})

    def delete_document(self, agent_id: str, document_id: str) -> Tuple[bool, Dict]:
        """Delete a document from an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully deleted
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("DELETE", f"/agents/{agent_id}/documents/{document_id}")

    # ================================================================
    # DOCUMENT METADATA OPERATIONS
    # ================================================================

    def get_document_metadata(self, agent_id: str, document_id: str) -> Tuple[bool, Dict]:
        """View document metadata.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.

        Returns:
            Tuple of (success: bool, response: Dict with document metadata)

        Responses:
            - 200: Successfully returned
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/documents/{document_id}/metadata")

    def create_document_metadata(self, agent_id: str, document_id: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Create/update document metadata via POST.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.
            metadata: object (required) - Metadata key-value pairs to set.

        Request Body:
            - Custom metadata object with key-value pairs

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully updated
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/documents/{document_id}/metadata", metadata)

    def update_document_metadata(self, agent_id: str, document_id: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Update document metadata via PUT.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.
            metadata: object (required) - Metadata key-value pairs to update.

        Request Body:
            - Custom metadata object with key-value pairs

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully updated
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("PUT", f"/agents/{agent_id}/documents/{document_id}/metadata", metadata)

    # ================================================================
    # DOCUMENT RETRIEVAL OPERATIONS
    # ================================================================

    def get_document(self, agent_id: str, document_id: str) -> Tuple[bool, Dict]:
        """Retrieve an agent document by ID.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.

        Returns:
            Tuple of (success: bool, response: Dict with document details)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/documents/{document_id}")

    def download_document(self, agent_id: str, document_id: str, doc_type: str, session_id: str = None) -> Tuple[bool, Dict]:
        """Download a document from an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.
            doc_type: string (required) - Type of document to download.
            session_id: string (optional) - Session ID for tracking.

        Returns:
            Tuple of (success: bool, response: Dict with document content/binary)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        url = f"/agents/{agent_id}/documents/{document_id}/download?docType={doc_type}"
        if session_id:
            url += f"&sessionId={session_id}"
        return self._request("GET", url)

    def download_document_figure(self, agent_id: str, document_id: str, figure_id: str) -> Tuple[bool, Dict]:
        """Download a figure/image from a document.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.
            figure_id: string (required) - Unique ID for the figure/image.

        Returns:
            Tuple of (success: bool, response: Dict with figure content/binary)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/documents/{document_id}/figures/{figure_id}/download")

    # ================================================================
    # DOCUMENT UPLOAD OPERATIONS
    # ================================================================

    def upload_data(self, agent_id: str, data_upload_config: Dict) -> Tuple[bool, Dict]:
        """Upload and index data/document to an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            data_upload_config: CognitiveAgentDocumentConfig (required) - Document configuration.

        Request Body (CognitiveAgentDocumentConfig):
            - embeddingModel: string - Embedding model name
            - chunkingStrategy: string - RECURSIVE_CHARACTER_SPLIT, TOKEN_SPLIT, PAGE_SPLIT
            - tokenSplitCount: integer - Token count for splitting
            - metadata: object - Custom metadata
            - dataFile: binary - The file to upload
            - ocrFile: binary (optional) - OCR file if applicable

        Returns:
            Tuple of (success: bool, response: Dict with upload result)

        Responses:
            - 200: Successfully created
            - 400: Bad Request
            - 500: Internal Server Error

        Note:
            For binary file uploads, use requests library directly with multipart/form-data.
            This method handles JSON-based data upload configuration.
        """
        return self._request("POST", f"/agents/{agent_id}/upload-data", data_upload_config)

    def upload_index_data(self, agent_id: str, data_upload_config: Dict) -> Tuple[bool, Dict]:
        """Upload and index data to an agent (alternative endpoint).

        Args:
            agent_id: string (required) - Unique ID for Agent.
            data_upload_config: CognitiveAgentDocumentConfig (required) - Document configuration.

        Request Body (CognitiveAgentDocumentConfig):
            - embeddingModel: string - Embedding model name
            - chunkingStrategy: string - RECURSIVE_CHARACTER_SPLIT, TOKEN_SPLIT, PAGE_SPLIT
            - tokenSplitCount: integer - Token count for splitting
            - metadata: object - Custom metadata
            - dataFile: binary - The file to upload
            - ocrFile: binary (optional) - OCR file if applicable

        Returns:
            Tuple of (success: bool, response: Dict with upload result)

        Responses:
            - 200: Successfully created
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/upload-index-data", data_upload_config)

    # ================================================================
    # CHAT OPERATIONS
    # ================================================================

    def chat(self, agent_id: str, message: str, session_id: str = None) -> Tuple[bool, Dict]:
        """Chat with an agent.

        Args:
            agent_id: string (required) - The agent ID for the chat request.
            message: string (required) - Content of the request (user prompt).
            session_id: string (optional) - Session ID for conversation continuity.

        Request Body (ElizaChatRequest):
            - agentId: string (required) - The agent ID
            - content: string (required) - Content of the request
            - elzSessionId: string (required) - Session ID
            - elzRequestCount: integer (required) - Request count in session
            - systemPrompt: string - Custom system prompt
            - temperature: number - Temperature for response generation
            - maxTokens: integer - Maximum tokens to generate
            - retrieverStrategy: string - Retriever strategy override
            - useHistory: boolean - Use conversation history
            - returnRagContext: boolean - Return RAG context used
            - jsonResponse: boolean - Return response in JSON format
            - stream: boolean - Stream response

        Returns:
            Tuple of (success: bool, response: Dict with chat response)

        Responses:
            - 200: Successfully processed
            - 201: Success
            - 400: Bad Request
            - 500: Internal Server Error
        """
        data = {
            "agentId": agent_id,
            "content": message
        }
        if session_id:
            data["elzSessionId"] = session_id
        return self._request("POST", "/agents/chat", data, timeout=120)

    def query_agent(self, agent_id: str, query: str) -> Tuple[bool, Dict]:
        """Query an agent (alias for chat).

        Args:
            agent_id: string (required) - The agent ID.
            query: string (required) - Query content.

        Returns:
            Tuple of (success: bool, response: Dict with chat response)
        """
        return self.chat(agent_id, query)

    # ================================================================
    # CHAT BULK OPERATIONS
    # ================================================================

    def chat_bulk(self, requests: list, is_async: bool = False) -> Tuple[bool, Dict]:
        """Chat with agent in bulk (multiple requests).

        Args:
            requests: array[ElizaChatRequest] (required) - List of chat requests.
            is_async: boolean (optional) - Process requests asynchronously.

        Request Body (BulkWorkbenchChatRequest):
            - async: boolean - Is Async processing
            - requests: array[object] - Chat Requests, each containing:
                - agentId: string (required) - The agent ID
                - content: string (required) - Content of the request
                - elzSessionId: string (required) - Session ID
                - elzRequestCount: integer (required) - Request count in session
                - systemPrompt: string - Custom system prompt
                - temperature: number - Temperature for response generation
                - maxTokens: integer - Maximum tokens to generate
                - retrieverStrategy: string - Retriever strategy override
                - useHistory: boolean - Use conversation history
                - returnRagContext: boolean - Return RAG context used
                - jsonResponse: boolean - Return response in JSON format
                - stream: boolean - Stream response
                - promptGroupId: string - Prompt Group Id
                - promptId: string - Prompt Id
                - modelId: string - Model Id
                - agentDocIds: array[string] - Limit to specific documents
                - indexWhereClause: string - Custom filter for vector index
                - metadataFilterExpression: string - Custom metadata filter

        Returns:
            Tuple of (success: bool, response: Dict with bulk chat results)

        Responses:
            - 200: Successfully processed
            - 201: Success
            - 400: Bad Request
            - 500: Internal Server Error
        """
        data = {
            "async": is_async,
            "requests": requests
        }
        return self._request("POST", "/agents/chat-bulk", data, timeout=300)

    def chat_bulk_extended(self, requests: list, agent_doc_ids: list = None, is_async: bool = False) -> Tuple[bool, Dict]:
        """Chat with agent in bulk for each document/prompt/prompt group.

        Args:
            requests: array[ElizaChatRequest] (required) - List of chat requests.
            agent_doc_ids: array[string] (optional) - Document IDs to process across.
            is_async: boolean (optional) - Process requests asynchronously.

        Request Body (ExtendedWorkbenchChatRequest):
            - async: boolean - Is Async processing
            - requests: array[object] - Chat Requests (same schema as chat_bulk)
            - agentDocIds: array[string] - Document IDs to iterate over.

        Use Case:
            Execute the same prompt across multiple documents, or multiple prompts
            across document sets. Useful for batch analysis, testing, and evaluation.

        Returns:
            Tuple of (success: bool, response: Dict with extended bulk chat results)

        Responses:
            - 200: Successfully processed
            - 201: Success
            - 400: Bad Request
            - 500: Internal Server Error
        """
        data = {
            "async": is_async,
            "requests": requests
        }
        if agent_doc_ids:
            data["agentDocIds"] = agent_doc_ids
        return self._request("POST", "/agents/chat-bulk-extended", data, timeout=300)

    # ================================================================
    # A2A OPERATIONS
    # ================================================================

    def register_a2a_server(self, discovery_url: str) -> Tuple[bool, Dict]:
        """Register an A2A server.

        Args:
            discovery_url: A2A server URL.

        Request Body:
            RegisterA2AServerRequest: {discoveryUrl: string}

        Returns:
            Tuple of (success: bool, response: Dict)
        """
        return self._request("POST", "/a2a/servers/register", {"discoveryUrl": discovery_url})

    def register_a2a_server_to_agent(self, server_id: str, agent_id: str) -> Tuple[bool, Dict]:
        """Register an A2A server to an agent.

        Args:
            server_id: UUID of the A2A server.
            agent_id: UUID of the agent.

        Returns:
            Tuple of (success: bool, response: Dict)
        """
        return self._request("POST", f"/a2a/servers/{server_id}/agents/{agent_id}")

    def list_a2a_servers(self, with_owner: bool = None) -> Tuple[bool, Dict]:
        """List A2A servers.

        Args:
            with_owner: Optional; include owner information.

        Returns:
            Tuple of (success: bool, response: Dict with server list)
        """
        url = "/a2a/servers/list"
        if with_owner is not None:
            url += f"?withOwner={str(with_owner).lower()}"
        return self._request("POST", url)

    def delete_a2a_server(self, server_id: str) -> Tuple[bool, Dict]:
        """Delete an A2A server.

        Args:
            server_id: UUID of the A2A server to delete.

        Returns:
            Tuple of (success: bool, response: Dict)
        """
        return self._request("DELETE", f"/a2a/servers/{server_id}")

    # ================================================================
    # ACTIVITY OPERATIONS
    # ================================================================

    def get_agent_activity(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get activity for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with activity data)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/activity")

    def get_agent_activity_users(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get user activity for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with user activity data)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/activity/users")

    def get_agent_activity_analytics(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get activity analytics for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with analytics data)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/activity/analytics")

    def get_all_users_activity(self) -> Tuple[bool, Dict]:
        """Get activity for all users.

        Returns:
            Tuple of (success: bool, response: Dict with all users activity)

        Responses:
            - 200: Successfully retrieved
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", "/agents/activity/users")

    # ================================================================
    # HISTORY OPERATIONS
    # ================================================================

    def get_agent_history(self, agent_id: str) -> Tuple[bool, Dict]:
        """Retrieve an agent's history.

        Retrieves the history of changes made to an Agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with history data)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/history")

    # ================================================================
    # USER OPERATIONS
    # ================================================================

    def get_agent_users(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get user list for a given agent.

        Get User Access List for the agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with user list)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/users")

    def get_user_initiatives(self) -> Tuple[bool, Dict]:
        """Get initiatives for current user.

        Returns:
            Tuple of (success: bool, response: Dict with initiatives list)

        Responses:
            - 200: OK
        """
        return self._request("GET", "/agents/users/initiatives")

    def get_top_questions(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get top questions asked to the agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with top questions)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/{agent_id}/top-questions")

    # ================================================================
    # MODELS & STRATEGIES OPERATIONS
    # ================================================================

    def get_models(self, initiative_id: str = None, return_all: bool = None) -> Tuple[bool, Dict]:
        """Get available models for agents.

        Gets list of available models for an agent.

        Args:
            initiative_id: string (optional) - ELZ Initiative Id.
            return_all: boolean (optional) - Return all models regardless of API visibility.

        Returns:
            Tuple of (success: bool, response: Dict with models list)

        Responses:
            - 200: OK
        """
        url = "/agents/models"
        params = []
        if initiative_id:
            params.append(f"elzInitiativeId={initiative_id}")
        if return_all is not None:
            params.append(f"returnAll={str(return_all).lower()}")
        if params:
            url += "?" + "&".join(params)
        return self._request("GET", url)

    def get_chunking_strategies(self) -> Tuple[bool, Dict]:
        """Get available chunking strategies.

        Gets chunking strategies for document processing.

        Returns:
            Tuple of (success: bool, response: Dict with chunking strategies)

        Responses:
            - 200: OK
        """
        return self._request("GET", "/agents/chunking-strategies")

    # ================================================================
    # CHUNK OPERATIONS
    # ================================================================

    def update_chunk(self, agent_id: str, document_id: str, chunk_id: str, chunk_data: Dict) -> Tuple[bool, Dict]:
        """Update a document chunk.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Document.
            chunk_id: string (required) - Unique ID for Chunk.
            chunk_data: ChunkUpdateVo containing chunk update data.

        Request Body (ChunkUpdateVo):
            - tags: string - Tags for the chunk
            - chunkType: enum (FULL, PARTIAL) - Type of the chunk
            - valueDate: integer - Value date
            - docChunkIndex: string - Chunk Index

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully created
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("PUT", f"/agents/{agent_id}/documents/{document_id}/chunks/{chunk_id}", chunk_data)

    def delete_chunk(self, agent_id: str, document_id: str, chunk_id: str) -> Tuple[bool, Dict]:
        """Delete a document chunk.

        Deletes a text chunk from a document.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.
            chunk_id: string (required) - Unique ID for Agent Document's Chunk.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully deleted
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("DELETE", f"/agents/{agent_id}/documents/{document_id}/chunks/{chunk_id}")

    # ================================================================
    # DOCUMENT RE-INDEX OPERATIONS
    # ================================================================

    def reindex_document(self, agent_id: str, document_id: str) -> Tuple[bool, Dict]:
        """Re-index a document.

        Triggers a re-indexing job for the document to refresh embeddings.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            document_id: string (required) - Unique ID for Agent's Document.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully started indexing job
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/documents/{document_id}/re-index")

    # ================================================================
    # VIRTUAL CHUNK OPERATIONS
    # ================================================================

    def create_virtual_chunk(self, agent_id: str, chunk_data: Dict) -> Tuple[bool, Dict]:
        """Create a virtual chunk.

        Creates a virtual text chunk for an agent document.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            chunk_data: VirtualChunkCreateVo containing chunk configuration.

        Request Body (VirtualChunkCreateVo):
            - agentId: string - Agent ID
            - agentDocId: string - Agent Document ID
            - chunkTxt: string - Chunk Text
            - sessionId: string - Session ID
            - vectorMetadata: object - Vector metadata
            - auxMetadata: object - Aux metadata
            - valueDate: integer - Value Date
            - tags: string - Tags to be added with chunks
            - chunkType: enum (FULL, PARTIAL) - Type of the chunk
            - docChunkIndex: integer - Index of the chunk
            - extractExtendedAttributes: boolean - Extract Extended Attributes

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully created
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/chunks/virtual", chunk_data)

    # ================================================================
    # TIER 3: AGENT PROMOTE OPERATIONS
    # ================================================================

    def promote_agent(self, agent_id: str) -> Tuple[bool, Dict]:
        """Promote an agent to the next environment.

        Promotes an Agent and all its resources (nuggets, prompts, functions)
        to the next higher environment. Creates a GitLab branch and calls
        REST APIs on the target environment to create the resources.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully promoted
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/promote")

    # ================================================================
    # TIER 3: INDEX SEARCH OPERATIONS
    # ================================================================

    def search_index(self, agent_id: str, search_data: Dict) -> Tuple[bool, Dict]:
        """Search vector DB index.

        Searches the vector database index for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            search_data: SearchIndexRequest containing search parameters.

        Request Body (SearchIndexRequest):
            - agentId: string - Agent ID
            - whereCondition: string - Where condition in request
            - metadataFilterExpression: string - Custom Filter Expression for Metadata
            - agentDocIds: array[string] - Optional list of agentDocIds to filter from
            - embeddingQuery: string - Embedding query
            - embeddingModelId: string - Embedding model ID
            - embeddingFieldName: string - Embedding field name
            - chunkType: enum (FULL, PARTIAL) - Chunk types to search in
            - orderby: string - Order By
            - highlight: string - Highlight Text
            - chunksToReturn: integer - Number of chunks to return
            - returnDocumentMetadata: boolean - Return document metadata
            - selectColumns: string - Select columns
            - fullTextSearch: object - Full Text search options

        Returns:
            Tuple of (success: bool, response: Dict with search results)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/index/search", search_data)

    def search_index_cosmosdb(self, agent_id: str, search_data: Dict) -> Tuple[bool, Dict]:
        """Search CosmosDB vector index.

        Searches the CosmosDB vector database index for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            search_data: SearchIndexRequest containing search parameters.

        Request Body (SearchIndexRequest):
            - Same as search_index

        Returns:
            Tuple of (success: bool, response: Dict with search results)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/index-cosmosdb/search", search_data)

    # ================================================================
    # TIER 3: IDENTITY OPERATIONS
    # ================================================================

    def add_agent_identity(self, agent_id: str, identity_data: Dict) -> Tuple[bool, Dict]:
        """Add identity to an agent.

        Configures identity settings for an agent including avatar and credentials.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            identity_data: CognitiveAgentIdentity containing identity configuration.

        Request Body (CognitiveAgentIdentity):
            - displayName: string - Display name
            - principalName: string - Principal name
            - principalId: string - Principal ID
            - roleCode: string - Role code
            - managerDisplayName: string - Manager display name
            - managerPrincipalName: string - Manager principal name
            - avatarCharacter: string - Avatar character
            - avatarVoice: string - Avatar voice
            - avatarStyle: string - Avatar style
            - avatarBackgroundColor: string - Avatar background color
            - avatarBackgroundImageUrl: string - Avatar background image URL
            - secretEnv: string - Secret environment
            - secretOrgId: string - Secret org ID
            - secretFamily: string - Secret family
            - secretApp: string - Secret app
            - username: string - Username
            - password: string - Password
            - realtimeVoice: enum (alloy, ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar)

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully processed
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/identity", identity_data)

    def delete_agent_identity(self, agent_id: str) -> Tuple[bool, Dict]:
        """Delete identity from an agent.

        Removes identity configuration from an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully processed
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("DELETE", f"/agents/{agent_id}/identity")

    # ================================================================
    # TIER 3: IDEAS/VOTES OPERATIONS
    # ================================================================

    def get_ideas(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get ideas for an agent.

        Retrieves all ideas associated with an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with ideas list)

        Responses:
            - 200: OK
        """
        return self._request("GET", f"/agents/{agent_id}/ideas")

    def vote_idea(self, agent_id: str, idea_id: str) -> Tuple[bool, Dict]:
        """Upvote an idea.

        Records a vote for a specific idea.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            idea_id: string (required) - Unique ID for Idea.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: OK
        """
        return self._request("POST", f"/agents/{agent_id}/ideas/{idea_id}/votes")

    def delete_idea(self, agent_id: str, idea_id: str) -> Tuple[bool, Dict]:
        """Delete an idea.

        Removes an idea from an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            idea_id: string (required) - Unique ID for Idea.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: OK
        """
        return self._request("DELETE", f"/agents/{agent_id}/ideas/{idea_id}")

    # ================================================================
    # TIER 3: HASHES OPERATIONS (MERKLE DAG)
    # ================================================================

    def list_hashes(self, agent_id: str) -> Tuple[bool, Dict]:
        """List Merkle DAG hashes.

        Retrieves the list of hashes for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with hashes list)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/hashes/list")

    def create_hash(self, agent_id: str, request_params: Dict = None) -> Tuple[bool, Dict]:
        """Create a Merkle DAG hash.

        Creates a new hash for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            request_params: HashCreateRequest parameters (optional).

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        url = f"/agents/{agent_id}/hashes/create"
        if request_params:
            return self._request("POST", url, request_params)
        return self._request("POST", url)

    def get_hash(self, agent_id: str, include_documents: bool = False) -> Tuple[bool, Dict]:
        """Get Merkle DAG hash.

        Retrieves the current hash for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            include_documents: boolean (optional) - Include documents in hash.

        Returns:
            Tuple of (success: bool, response: Dict with hash)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        url = f"/agents/{agent_id}/hash"
        if include_documents:
            url += "?includeDocuments=true"
        return self._request("GET", url)

    def delete_hash(self, agent_id: str, hash_value: str) -> Tuple[bool, Dict]:
        """Delete a Merkle DAG hash.

        Removes a specific hash from an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            hash_value: string (required) - Hash value to delete.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("DELETE", f"/agents/{agent_id}/hashes/{hash_value}")

    # ================================================================
    # TIER 3: AGENT DISABLE OPERATIONS
    # ================================================================

    def disable_agent(self, agent_id: str) -> Tuple[bool, Dict]:
        """Disable an agent.

        Disables an agent, making it inactive.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully disabled
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/disable")

    # ================================================================
    # TIER 3: BACK-TESTING OPERATIONS
    # ================================================================

    def back_testing(self, agent_id: str, test_data: Dict) -> Tuple[bool, Dict]:
        """Run agent back-testing.

        Runs back-testing for an agent to compare different model configurations.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            test_data: AgentBackTestingRequest containing test configuration.

        Request Body (AgentBackTestingRequest):
            - sessionId: string - Session ID
            - baseModelId: string - Base Model ID
            - compareModelId: string - Compare Model ID
            - challengerModelId: string - Challenger Model ID
            - chatRequests: array[ElizaChatRequest] - Chat requests to test

        Returns:
            Tuple of (success: bool, response: Dict with test results)

        Responses:
            - 200: Successfully processed
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", f"/agents/{agent_id}/back-testing", test_data)

    # ================================================================
    # TIER 3: UPVOTE OPERATIONS
    # ================================================================

    def upvote(self, vote_data: Dict) -> Tuple[bool, Dict]:
        """Submit an upvote.

        Records an upvote for various entity types.

        Args:
            vote_data: CognitiveVote containing vote details.

        Request Body (CognitiveVote):
            - cogVoteId: string - Vote ID
            - voteCategory: string - Vote category
            - entityKey: string - Entity key
            - entityType: enum (COG_PROMPT, COG_AGENT, COG_QUESTION, COG_IDEA)
            - userId: string - User ID

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: OK
        """
        return self._request("POST", "/agents/upvote", vote_data)

    # ================================================================
    # TIER 3: RESOURCE CALL OPERATIONS
    # ================================================================

    def call_resource(self, ern_request: Dict) -> Tuple[bool, Dict]:
        """Call a resource by ERN.

        Retrieves a resource by its Eliza Resource Name (ERN) and calls
        the respective method.

        Args:
            ern_request: ErnRequest containing the resource call details.

        Request Body (ErnRequest):
            - ern: string - Eliza Resource Name (e.g., ern:eliza:agent:<agentId>)
            - data: object - Optional data map to pass to the resource call

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found - Resource not found
            - 400: Bad Request - Invalid ERN format
            - 500: Internal Server Error
        """
        return self._request("POST", "/agents/resource/call", ern_request)

    # ================================================================
    # TIER 3: IMPORT OPERATIONS
    # ================================================================

    def import_agent(self, import_data: Dict) -> Tuple[bool, Dict]:
        """Import agent resources.

        Imports an agent and all its resources (nuggets, prompts, functions)
        from a promotion request. This endpoint is called by lower environments
        to create resources on higher environments.

        Args:
            import_data: AgentResourcesImportRequest containing import data.

        Request Body (AgentResourcesImportRequest):
            - agent: object - Agent configuration
            - nuggets: array[object] - List of nuggets to import
            - prompts: array[object] - List of prompts to import
            - functions: array[object] - List of functions to import
            - sourceEnvironment: string - Source environment this data came from
            - initiatedBy: string - User who initiated the promotion

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully imported
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", "/agents/import", import_data)

    # ================================================================
    # TIER 3: COMPUTER USE OPERATIONS
    # ================================================================

    def computer_use(self, computer_request: Dict) -> Tuple[bool, Dict]:
        """Call computer use.

        Executes computer use operations for automation tasks.

        Args:
            computer_request: ComputerUseRequest containing the request details.

        Request Body (ComputerUseRequest):
            - computerAddress: string - Computer address
            - instruction: string - Instruction to execute
            - systemPrompt: string - System prompt

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: OK
        """
        return self._request("POST", "/agents/computer-use", computer_request)

    # ================================================================
    # TIER 3: ACCESS CONTROL OPERATIONS
    # ================================================================

    def add_agent_access(self, access_data: Dict) -> Tuple[bool, Dict]:
        """Provide access to an agent.

        Grants user access to an agent.

        Args:
            access_data: UserAuthorization containing access configuration.

        Request Body (UserAuthorization):
            - userId: string - User ID | Group Id
            - userType: string - User Type (COMMIT_ID | GROUP_ID)
            - authType: string - Authorization Type (AGENT_ENTITLEMENT | GROUP_ENTITLEMENT)
            - authId: string - Authorization ID
            - authIdType: string - Authorization ID Type
            - userRole: string - User Role (OWNER | USER)
            - orgId: string - Organization ID
            - tenantId: string - Tenant ID

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", "/agents/access", access_data)

    def remove_agent_access(self, agent_id: str, user_id: str, role: str) -> Tuple[bool, Dict]:
        """Remove agent access.

        Revokes user access from an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            user_id: string (required) - User ID to remove access from.
            role: string (required) - Role for which access is removed.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 400: Bad Request
            - 500: Internal Server Error
        """
        url = f"/agents/access?agentId={agent_id}&userId={user_id}&role={role}"
        return self._request("DELETE", url)

    def add_auth_access(self, auth_data: Dict) -> Tuple[bool, Dict]:
        """Provide auth access to a resource.

        Grants authorization access to a resource.

        Args:
            auth_data: UserAuthorization containing access configuration.

        Request Body (UserAuthorization):
            - Same as add_agent_access

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("POST", "/agents/access-auth", auth_data)

    def remove_auth_access(self, agent_id: str, user_id: str, role: str) -> Tuple[bool, Dict]:
        """Remove auth access from a resource.

        Revokes authorization access from a resource.

        Args:
            agent_id: string (required) - Unique ID for Agent.
            user_id: string (required) - User ID to remove access from.
            role: string (required) - Role for which access is removed.

        Returns:
            Tuple of (success: bool, response: Dict)

        Responses:
            - 200: Successfully retrieved
            - 400: Bad Request
            - 500: Internal Server Error
        """
        url = f"/agents/access-auth?agentId={agent_id}&userId={user_id}&role={role}"
        return self._request("DELETE", url)

    # ================================================================
    # TIER 3: DATASOURCE OPERATIONS
    # ================================================================

    def get_datasource_list(self, agent_id: str) -> Tuple[bool, Dict]:
        """Get datasource list for an agent.

        Retrieves the list of data sources configured for an agent.

        Args:
            agent_id: string (required) - Unique ID for Agent.

        Returns:
            Tuple of (success: bool, response: Dict with datasource list)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/datasource/{agent_id}")

    # ================================================================
    # TIER 3: CONTROL FLAG OPERATIONS
    # ================================================================

    def get_agents_by_control_flag(self, control_flag: str) -> Tuple[bool, Dict]:
        """Get agent list for a given control flag.

        Retrieves all agents that have the specified control flag.

        Args:
            control_flag: string (required) - Control flag to search for.

        Returns:
            Tuple of (success: bool, response: Dict with agents list)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/control-flag/{control_flag}")

    # ================================================================
    # TIER 3: APP LIST OPERATIONS
    # ================================================================

    def get_agents_by_app_id(self, app_id: str) -> Tuple[bool, Dict]:
        """Get agent list for a given app ID.

        Retrieves all agents associated with the specified app ID.

        Args:
            app_id: string (required) - App ID to search for.

        Returns:
            Tuple of (success: bool, response: Dict with agents list)

        Responses:
            - 200: Successfully retrieved
            - 404: Not Found
            - 400: Bad Request
            - 500: Internal Server Error
        """
        return self._request("GET", f"/agents/app/{app_id}")


def get_client(jwt_token: str, env: str = "QA") -> ElizaClient:
    """Create and return an ElizaClient instance."""
    return ElizaClient(jwt_token, env)