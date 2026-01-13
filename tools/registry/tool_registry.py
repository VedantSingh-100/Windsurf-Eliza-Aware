"""
Tool Registry - Central definitions for all API operation categories.

HYBRID APPROACH: This file stores FULL schemas as authoritative reference.
The category_router.py uses these as fallback if docstring extraction fails.

Schema structure for each operation:
- method: Client method name
- params: Parameter list for the handler
- required: Required parameters
- description: Short description
- args: Full parameter descriptions (mirrors docstring Args)
- request_body: Schema name and fields (mirrors docstring Request Body)
- responses: Status codes and descriptions (mirrors docstring Responses)
"""

from typing import Dict, Any

# JSON Schema for common parameters
PARAM_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "agent_id": {
        "type": "string",
        "description": "Unique ID for the Agent (UUID format)"
    },
    "nugget_id": {
        "type": "string",
        "description": "Unique ID for the Nugget (UUID format)"
    },
    "document_id": {
        "type": "string",
        "description": "Unique ID for the Document (UUID format)"
    },
    "chunk_id": {
        "type": "string",
        "description": "Unique ID for the Chunk (UUID format)"
    },
    "server_id": {
        "type": "string",
        "description": "Unique ID for the A2A Server (UUID format)"
    },
    "figure_id": {
        "type": "string",
        "description": "Unique ID for the figure/image in a document"
    },
    "message": {
        "type": "string",
        "description": "Message content to send to the agent"
    },
    "query": {
        "type": "string",
        "description": "Query content to send to the agent"
    },
    "session_id": {
        "type": "string",
        "description": "Session ID for conversation continuity"
    },
    "requests": {
        "type": "array",
        "items": {"type": "object"},
        "description": "Array of chat request objects (ElizaChatRequest)"
    },
    "agent_doc_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Array of document IDs to process"
    },
    "is_async": {
        "type": "boolean",
        "description": "Process requests asynchronously"
    },
    "data": {
        "type": "object",
        "description": "Key-value pairs for nugget execution"
    },
    "search_data": {
        "type": "object",
        "description": "Search request parameters (NuggetSearchRequest)"
    },
    "discovery_url": {
        "type": "string",
        "description": "A2A server discovery URL"
    },
    "with_owner": {
        "type": "boolean",
        "description": "Include owner information in response"
    },
    "doc_type": {
        "type": "string",
        "description": "Type of document to download"
    },
    "metadata": {
        "type": "object",
        "description": "Metadata key-value pairs"
    },
    "chunk_data": {
        "type": "object",
        "description": "Chunk update data (ChunkUpdateVo)"
    },
    "initiative_id": {
        "type": "string",
        "description": "ELZ Initiative ID (format: ELZI-{userid})"
    },
    "return_all": {
        "type": "boolean",
        "description": "Return all results regardless of API visibility"
    },
}

# Central registry of all operation categories with FULL schemas
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # CHAT OPERATIONS
    # =========================================================================
    "chat_operations": {
        "description": "Chat with Eliza agents - send messages and receive responses",
        "when_to_use": [
            "User wants to send a message to an agent",
            "User wants to query an agent for information",
            "User needs batch/bulk chat processing",
            "User wants to run same prompt across multiple documents"
        ],
        "operations": {
            "chat": {
                "method": "chat",
                "params": ["agent_id", "message", "session_id"],
                "required": ["agent_id", "message"],
                "description": "Send a message to an agent and get a response",
                "args": {
                    "agent_id": "string (required) - The agent ID for the chat request",
                    "message": "string (required) - Content of the request (user prompt)",
                    "session_id": "string (optional) - Session ID for conversation continuity"
                },
                "request_body": {
                    "schema_name": "ElizaChatRequest",
                    "fields": {
                        "agentId": {"type": "string", "required": True, "description": "The agent ID"},
                        "content": {"type": "string", "required": True, "description": "Content of the request"},
                        "elzSessionId": {"type": "string", "required": True, "description": "Session ID"},
                        "elzRequestCount": {"type": "integer", "required": True, "description": "Request count in session"},
                        "systemPrompt": {"type": "string", "required": False, "description": "Custom system prompt"},
                        "temperature": {"type": "number", "required": False, "description": "Temperature for response generation (0.0-1.0)"},
                        "maxTokens": {"type": "integer", "required": False, "description": "Maximum tokens to generate"},
                        "retrieverStrategy": {"type": "string", "required": False, "description": "Retriever strategy: STANDARD, REASON, MULTI_QUERY"},
                        "useHistory": {"type": "boolean", "required": False, "description": "Use conversation history"},
                        "returnRagContext": {"type": "boolean", "required": False, "description": "Return RAG context used"},
                        "jsonResponse": {"type": "boolean", "required": False, "description": "Return response in JSON format"},
                        "stream": {"type": "boolean", "required": False, "description": "Stream response"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "201": "Success",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "query": {
                "method": "query_agent",
                "params": ["agent_id", "query"],
                "required": ["agent_id", "query"],
                "description": "Query an agent (alias for chat)",
                "args": {
                    "agent_id": "string (required) - The agent ID",
                    "query": "string (required) - Query content"
                },
                "responses": {
                    "200": "Successfully processed"
                }
            },
            "bulk": {
                "method": "chat_bulk",
                "params": ["requests", "is_async"],
                "required": ["requests"],
                "description": "Send multiple chat requests in bulk",
                "args": {
                    "requests": "array[ElizaChatRequest] (required) - List of chat requests",
                    "is_async": "boolean (optional) - Process requests asynchronously"
                },
                "request_body": {
                    "schema_name": "BulkWorkbenchChatRequest",
                    "fields": {
                        "async": {"type": "boolean", "required": False, "description": "Is Async processing"},
                        "requests": {"type": "array", "required": True, "description": "Chat Requests array"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "201": "Success",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "bulk_extended": {
                "method": "chat_bulk_extended",
                "params": ["requests", "agent_doc_ids", "is_async"],
                "required": ["requests"],
                "description": "Bulk chat across multiple documents",
                "args": {
                    "requests": "array[ElizaChatRequest] (required) - List of chat requests",
                    "agent_doc_ids": "array[string] (optional) - Document IDs to process across",
                    "is_async": "boolean (optional) - Process requests asynchronously"
                },
                "request_body": {
                    "schema_name": "ExtendedWorkbenchChatRequest",
                    "fields": {
                        "async": {"type": "boolean", "required": False, "description": "Is Async processing"},
                        "requests": {"type": "array", "required": True, "description": "Chat Requests array"},
                        "agentDocIds": {"type": "array", "required": False, "description": "Document IDs to iterate over"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "201": "Success",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # ANALYTICS OPERATIONS
    # =========================================================================
    "analytics_operations": {
        "description": "Agent usage analytics, activity tracking, and history",
        "when_to_use": [
            "User wants to see agent usage statistics",
            "User wants to know which users are using an agent",
            "User wants to see agent change history",
            "User wants to see top questions asked to an agent"
        ],
        "operations": {
            "activity": {
                "method": "get_agent_activity",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get activity data for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "users": {
                "method": "get_agent_activity_users",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get user activity for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "analytics": {
                "method": "get_agent_activity_analytics",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get analytics data for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "all_users": {
                "method": "get_all_users_activity",
                "params": [],
                "required": [],
                "description": "Get activity for all users",
                "args": {},
                "responses": {
                    "200": "Successfully retrieved",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "history": {
                "method": "get_agent_history",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get change history for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "top_questions": {
                "method": "get_top_questions",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get top questions asked to an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # A2A OPERATIONS
    # =========================================================================
    "a2a_operations": {
        "description": "Agent-to-Agent (A2A) server management",
        "when_to_use": [
            "User wants to register an A2A server",
            "User wants to connect an A2A server to an agent",
            "User wants to list available A2A servers",
            "User wants to delete an A2A server"
        ],
        "operations": {
            "register": {
                "method": "register_a2a_server",
                "params": ["discovery_url"],
                "required": ["discovery_url"],
                "description": "Register an A2A server",
                "args": {
                    "discovery_url": "string (required) - A2A server discovery URL"
                },
                "request_body": {
                    "schema_name": "RegisterA2AServerRequest",
                    "fields": {
                        "discoveryUrl": {"type": "string", "required": True, "description": "A2A server URL"}
                    }
                },
                "responses": {
                    "200": "Successfully registered"
                }
            },
            "register_to_agent": {
                "method": "register_a2a_server_to_agent",
                "params": ["server_id", "agent_id"],
                "required": ["server_id", "agent_id"],
                "description": "Register an A2A server to a specific agent",
                "args": {
                    "server_id": "string (required) - UUID of the A2A server",
                    "agent_id": "string (required) - UUID of the agent"
                },
                "responses": {
                    "200": "Successfully registered to agent"
                }
            },
            "list": {
                "method": "list_a2a_servers",
                "params": ["with_owner"],
                "required": [],
                "description": "List all A2A servers",
                "args": {
                    "with_owner": "boolean (optional) - Include owner information"
                },
                "responses": {
                    "200": "Successfully retrieved server list"
                }
            },
            "delete": {
                "method": "delete_a2a_server",
                "params": ["server_id"],
                "required": ["server_id"],
                "description": "Delete an A2A server",
                "args": {
                    "server_id": "string (required) - UUID of the A2A server to delete"
                },
                "responses": {
                    "200": "Successfully deleted"
                }
            }
        }
    },

    # =========================================================================
    # NUGGET EXECUTION
    # =========================================================================
    "nugget_execution": {
        "description": "Execute nuggets on agents - call, search, and run bulk operations",
        "when_to_use": [
            "User wants to execute a specific nugget",
            "User wants to call a nugget dynamically",
            "User wants to run multiple nuggets in bulk",
            "User wants to search for nuggets on an agent"
        ],
        "operations": {
            "call": {
                "method": "call_nugget",
                "params": ["agent_id", "nugget_id", "data"],
                "required": ["agent_id", "nugget_id", "data"],
                "description": "Execute a specific nugget by ID",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "nugget_id": "string (required) - UUID of the nugget to execute",
                    "data": "object (required) - Key-value pairs for nugget execution"
                },
                "request_body": {
                    "schema_name": "NuggetCallRequest",
                    "fields": {
                        "data": {"type": "object", "required": True, "description": "Key-value pairs for nugget execution"},
                        "sessionId": {"type": "string", "required": False, "description": "Optional session identifier"},
                        "requestId": {"type": "string", "required": False, "description": "Optional request identifier"}
                    }
                },
                "responses": {
                    "200": "Successfully executed"
                }
            },
            "call_dynamic": {
                "method": "call_dynamic_nugget",
                "params": ["agent_id", "data"],
                "required": ["agent_id", "data"],
                "description": "Call a dynamic nugget without specifying ID",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "data": "object (required) - Key-value pairs for nugget execution"
                },
                "request_body": {
                    "schema_name": "NuggetCallRequest",
                    "fields": {
                        "data": {"type": "object", "required": True, "description": "Key-value pairs for nugget execution"},
                        "sessionId": {"type": "string", "required": False, "description": "Optional session identifier"},
                        "requestId": {"type": "string", "required": False, "description": "Optional request identifier"},
                        "args": {"type": "array", "required": False, "description": "Optional string array of arguments"}
                    }
                },
                "responses": {
                    "200": "Successfully executed"
                }
            },
            "call_bulk": {
                "method": "call_bulk_nuggets",
                "params": ["agent_id", "data"],
                "required": ["agent_id", "data"],
                "description": "Execute multiple nuggets in bulk",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "data": "object (required) - Bulk nugget call request data"
                },
                "request_body": {
                    "schema_name": "NuggetCallBulkRequest",
                    "fields": {
                        "runKey": {"type": "string", "required": True, "description": "Identifier for the bulk run"},
                        "data": {"type": "object", "required": True, "description": "Key-value pairs for nugget execution"},
                        "nuggetIds": {"type": "array", "required": True, "description": "Array of nugget IDs to execute"}
                    }
                },
                "responses": {
                    "200": "Successfully executed bulk nuggets"
                }
            },
            "search": {
                "method": "search_nuggets",
                "params": ["agent_id", "search_data"],
                "required": ["agent_id", "search_data"],
                "description": "Search nuggets on an agent",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "search_data": "object (required) - Search request parameters"
                },
                "request_body": {
                    "schema_name": "NuggetSearchRequest",
                    "fields": {
                        "historicalSearch": {"type": "boolean", "required": False, "description": "Search historical nuggets"},
                        "nuggetId": {"type": "string", "required": False, "description": "Specific nugget ID to search"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved search results"
                }
            }
        }
    },

    # =========================================================================
    # DOCUMENT EXTENDED
    # =========================================================================
    "document_extended": {
        "description": "Extended document operations - retrieval, download, metadata, and reindexing",
        "when_to_use": [
            "User wants to retrieve a document by ID",
            "User wants to download a document or figure",
            "User wants to view or update document metadata",
            "User wants to re-index a document"
        ],
        "operations": {
            "get": {
                "method": "get_document",
                "params": ["agent_id", "document_id"],
                "required": ["agent_id", "document_id"],
                "description": "Retrieve a document by ID",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "download": {
                "method": "download_document",
                "params": ["agent_id", "document_id", "doc_type", "session_id"],
                "required": ["agent_id", "document_id", "doc_type"],
                "description": "Download a document",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document",
                    "doc_type": "string (required) - Type of document to download",
                    "session_id": "string (optional) - Session ID for tracking"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "download_figure": {
                "method": "download_document_figure",
                "params": ["agent_id", "document_id", "figure_id"],
                "required": ["agent_id", "document_id", "figure_id"],
                "description": "Download a figure/image from a document",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document",
                    "figure_id": "string (required) - Unique ID for the figure/image"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "get_metadata": {
                "method": "get_document_metadata",
                "params": ["agent_id", "document_id"],
                "required": ["agent_id", "document_id"],
                "description": "Get metadata for a document",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document"
                },
                "responses": {
                    "200": "Successfully returned",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "create_metadata": {
                "method": "create_document_metadata",
                "params": ["agent_id", "document_id", "metadata"],
                "required": ["agent_id", "document_id", "metadata"],
                "description": "Create/set document metadata",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document",
                    "metadata": "object (required) - Metadata key-value pairs to set"
                },
                "request_body": {
                    "schema_name": "MetadataObject",
                    "fields": {
                        "metadata": {"type": "object", "required": True, "description": "Custom metadata object with key-value pairs"}
                    }
                },
                "responses": {
                    "200": "Successfully updated",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "update_metadata": {
                "method": "update_document_metadata",
                "params": ["agent_id", "document_id", "metadata"],
                "required": ["agent_id", "document_id", "metadata"],
                "description": "Update existing document metadata",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document",
                    "metadata": "object (required) - Metadata key-value pairs to update"
                },
                "request_body": {
                    "schema_name": "MetadataObject",
                    "fields": {
                        "metadata": {"type": "object", "required": True, "description": "Custom metadata object with key-value pairs"}
                    }
                },
                "responses": {
                    "200": "Successfully updated",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "reindex": {
                "method": "reindex_document",
                "params": ["agent_id", "document_id"],
                "required": ["agent_id", "document_id"],
                "description": "Trigger re-indexing for a document",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document"
                },
                "responses": {
                    "200": "Successfully started indexing job",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # CHUNK OPERATIONS
    # =========================================================================
    "chunk_operations": {
        "description": "Document chunk management - create, update and delete chunks",
        "when_to_use": [
            "User wants to create a virtual chunk",
            "User wants to update a document chunk",
            "User wants to delete a document chunk",
            "User wants to modify chunk tags or type"
        ],
        "operations": {
            "update": {
                "method": "update_chunk",
                "params": ["agent_id", "document_id", "chunk_id", "chunk_data"],
                "required": ["agent_id", "document_id", "chunk_id", "chunk_data"],
                "description": "Update a document chunk",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Document",
                    "chunk_id": "string (required) - Unique ID for Chunk",
                    "chunk_data": "object (required) - Chunk update data"
                },
                "request_body": {
                    "schema_name": "ChunkUpdateVo",
                    "fields": {
                        "tags": {"type": "string", "required": False, "description": "Tags for the chunk"},
                        "chunkType": {"type": "string", "required": False, "description": "Type of the chunk: FULL or PARTIAL"},
                        "valueDate": {"type": "integer", "required": False, "description": "Value date"},
                        "docChunkIndex": {"type": "string", "required": False, "description": "Chunk Index"}
                    }
                },
                "responses": {
                    "200": "Successfully created",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_chunk",
                "params": ["agent_id", "document_id", "chunk_id"],
                "required": ["agent_id", "document_id", "chunk_id"],
                "description": "Delete a document chunk",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Agent's Document",
                    "chunk_id": "string (required) - Unique ID for Agent Document's Chunk"
                },
                "responses": {
                    "200": "Successfully deleted",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "create_virtual": {
                "method": "create_virtual_chunk",
                "params": ["agent_id", "chunk_data"],
                "required": ["agent_id", "chunk_data"],
                "description": "Create a virtual chunk",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "chunk_data": "object (required) - VirtualChunkCreateVo configuration"
                },
                "request_body": {
                    "schema_name": "VirtualChunkCreateVo",
                    "fields": {
                        "agentId": {"type": "string", "required": False, "description": "Agent ID"},
                        "agentDocId": {"type": "string", "required": True, "description": "Agent Document ID"},
                        "chunkTxt": {"type": "string", "required": True, "description": "Chunk Text"},
                        "sessionId": {"type": "string", "required": False, "description": "Session ID"},
                        "vectorMetadata": {"type": "object", "required": False, "description": "Vector metadata"},
                        "auxMetadata": {"type": "object", "required": False, "description": "Aux metadata"},
                        "valueDate": {"type": "integer", "required": False, "description": "Value Date"},
                        "tags": {"type": "string", "required": False, "description": "Tags to be added with chunks"},
                        "chunkType": {"type": "string", "required": False, "description": "Type of chunk (FULL, PARTIAL)"},
                        "docChunkIndex": {"type": "integer", "required": False, "description": "Index of the chunk"},
                        "extractExtendedAttributes": {"type": "boolean", "required": False, "description": "Extract Extended Attributes"}
                    }
                },
                "responses": {
                    "200": "Successfully created",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # SYSTEM OPERATIONS
    # =========================================================================
    "system_operations": {
        "description": "System information - available models, strategies, users, and initiatives",
        "when_to_use": [
            "User wants to see available LLM models",
            "User wants to see chunking strategies",
            "User wants to see user access list for an agent",
            "User wants to see their initiatives"
        ],
        "operations": {
            "get_models": {
                "method": "get_models",
                "params": ["initiative_id", "return_all"],
                "required": [],
                "description": "Get available LLM models",
                "args": {
                    "initiative_id": "string (optional) - ELZ Initiative Id (format: ELZI-{userid})",
                    "return_all": "boolean (optional) - Return all models regardless of API visibility"
                },
                "responses": {
                    "200": "OK"
                }
            },
            "get_chunking_strategies": {
                "method": "get_chunking_strategies",
                "params": [],
                "required": [],
                "description": "Get available chunking strategies",
                "args": {},
                "responses": {
                    "200": "OK - Returns: RECURSIVE_CHARACTER_SPLIT, TOKEN_SPLIT, PAGE_SPLIT"
                }
            },
            "get_agent_users": {
                "method": "get_agent_users",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get user access list for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "get_initiatives": {
                "method": "get_user_initiatives",
                "params": [],
                "required": [],
                "description": "Get initiatives for current user",
                "args": {},
                "responses": {
                    "200": "OK"
                }
            }
        }
    },

    # =========================================================================
    # AGENT CRUD OPERATIONS
    # =========================================================================
    "agent_crud": {
        "description": "Create, read, update, delete agents",
        "when_to_use": [
            "User wants to create a new agent",
            "User wants to get agent details",
            "User wants to update agent configuration",
            "User wants to delete an agent",
            "User wants to list their agents",
            "User wants to disable an agent"
        ],
        "operations": {
            "create": {
                "method": "create_agent",
                "params": ["agent_data"],
                "required": ["agent_data"],
                "description": "Create a new agent",
                "args": {
                    "agent_data": "object (required) - AgentCreateVo containing agent configuration"
                },
                "request_body": {
                    "schema_name": "AgentCreateVo",
                    "fields": {
                        "name": {"type": "string", "required": True, "description": "Agent Name"},
                        "description": {"type": "string", "required": False, "description": "Description of agent"},
                        "prompt": {"type": "string", "required": False, "description": "System prompt for the agent"},
                        "retrieverStrategy": {"type": "string", "required": False, "description": "Retriever strategy (STANDARD, REASON, etc.)"},
                        "llmModel": {"type": "string", "required": False, "description": "LLM model name"},
                        "initiativeId": {"type": "string", "required": True, "description": "Initiative ID (format: ELZI-{userid})"},
                        "controlFlags": {"type": "array", "required": False, "description": "Control flags (ADD_KNOWLEDGE, USE_HISTORY, etc.)"},
                        "agentType": {"type": "string", "required": False, "description": "Type of agent"},
                        "welcomeMessage": {"type": "string", "required": False, "description": "Welcome message displayed to user"},
                        "metadata": {"type": "object", "required": False, "description": "Custom metadata"},
                        "isActive": {"type": "boolean", "required": False, "description": "Toggle to activate/deactivate agent"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "get": {
                "method": "get_agent",
                "params": ["agent_id", "include_documents"],
                "required": ["agent_id"],
                "description": "Retrieve an agent by ID",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "include_documents": "boolean (optional) - Include documents in response"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "update": {
                "method": "update_agent",
                "params": ["agent_id", "updates"],
                "required": ["agent_id", "updates"],
                "description": "Update agent attributes",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "updates": "object (required) - AgentCreateVo containing fields to update"
                },
                "request_body": {
                    "schema_name": "AgentCreateVo",
                    "fields": {
                        "name": {"type": "string", "required": False, "description": "Agent Name"},
                        "description": {"type": "string", "required": False, "description": "Description of agent"},
                        "prompt": {"type": "string", "required": False, "description": "System prompt"},
                        "retrieverStrategy": {"type": "string", "required": False, "description": "Retriever strategy"},
                        "llmModel": {"type": "string", "required": False, "description": "LLM model name"},
                        "controlFlags": {"type": "array", "required": False, "description": "Control flags"},
                        "welcomeMessage": {"type": "string", "required": False, "description": "Welcome message"},
                        "metadata": {"type": "object", "required": False, "description": "Custom metadata"},
                        "isActive": {"type": "boolean", "required": False, "description": "Toggle to activate/deactivate agent"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_agent",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Delete an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully deleted",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "list": {
                "method": "list_agents",
                "params": ["offset", "limit"],
                "required": [],
                "description": "List agents for the current user",
                "args": {
                    "offset": "integer (optional) - Pagination offset. Default: 0",
                    "limit": "integer (optional) - Number of results. Default: 20"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "disable": {
                "method": "disable_agent",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Disable an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully disabled",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # NUGGET CRUD OPERATIONS
    # =========================================================================
    "nugget_crud": {
        "description": "Create, read, update, delete nuggets (code snippets attached to agents)",
        "when_to_use": [
            "User wants to create a new nugget",
            "User wants to get nugget details",
            "User wants to update nugget code or configuration",
            "User wants to delete a nugget"
        ],
        "operations": {
            "create": {
                "method": "create_nugget",
                "params": ["agent_id", "nugget_data"],
                "required": ["agent_id", "nugget_data"],
                "description": "Create a nugget on an agent",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "nugget_data": "object (required) - CognitiveAgentNugget configuration"
                },
                "request_body": {
                    "schema_name": "CognitiveAgentNugget",
                    "fields": {
                        "label": {"type": "string", "required": True, "description": "Nugget display name"},
                        "description": {"type": "string", "required": False, "description": "What the nugget does"},
                        "call": {"type": "object", "required": True, "description": "Code block with @type, language, and code"},
                        "prompt": {"type": "string", "required": False, "description": "When LLM should use this nugget"},
                        "params": {"type": "array", "required": False, "description": "Input parameters array"}
                    }
                },
                "responses": {
                    "200": "Successfully created",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "get": {
                "method": "get_nugget",
                "params": ["agent_id", "nugget_id"],
                "required": ["agent_id", "nugget_id"],
                "description": "Get nugget details by ID",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "nugget_id": "string (required) - UUID of the nugget"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "update": {
                "method": "update_nugget",
                "params": ["agent_id", "nugget_id", "updates", "is_default"],
                "required": ["agent_id", "nugget_id", "updates"],
                "description": "Update nugget code or configuration",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "nugget_id": "string (required) - UUID of the nugget",
                    "updates": "object (required) - Fields to update",
                    "is_default": "boolean (optional) - Make this the default nugget"
                },
                "responses": {
                    "200": "Successfully updated",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_nugget",
                "params": ["agent_id", "nugget_id"],
                "required": ["agent_id", "nugget_id"],
                "description": "Delete a nugget from an agent",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "nugget_id": "string (required) - UUID of the nugget"
                },
                "responses": {
                    "200": "Successfully deleted",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # FUNCTION CRUD OPERATIONS
    # =========================================================================
    "function_crud": {
        "description": "Create, read, delete functions on agents",
        "when_to_use": [
            "User wants to add a function to an agent",
            "User wants to get function details",
            "User wants to delete a function",
            "User wants to list all functions on an agent"
        ],
        "operations": {
            "add": {
                "method": "add_function",
                "params": ["agent_id", "function_data"],
                "required": ["agent_id", "function_data"],
                "description": "Create a function on an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "function_data": "object (required) - CognitiveAgentFunctionConfig"
                },
                "request_body": {
                    "schema_name": "CognitiveAgentFunctionConfig",
                    "fields": {
                        "funcNameKey": {"type": "string", "required": True, "description": "Function name key (identifier)"},
                        "label": {"type": "string", "required": True, "description": "Function text displayed to user"},
                        "prompt": {"type": "string", "required": False, "description": "Function prompt (when LLM should use this)"},
                        "functionType": {"type": "string", "required": True, "description": "Type: SQL, API, REST, PYTHON_STATIC, NUGGET, AGENT, etc."},
                        "nuggetId": {"type": "string", "required": False, "description": "Nugget ID (for NUGGET type)"},
                        "params": {"type": "array", "required": False, "description": "Function parameters"},
                        "returnResultDirectly": {"type": "boolean", "required": False, "description": "Return result without LLM processing"},
                        "code": {"type": "string", "required": False, "description": "Code (for PYTHON_STATIC type)"},
                        "dataSource": {"type": "string", "required": False, "description": "Data source name (for SQL type)"},
                        "sql": {"type": "string", "required": False, "description": "SQL query (for SQL type)"},
                        "httpMethod": {"type": "string", "required": False, "description": "HTTP method (for REST/API type)"},
                        "path": {"type": "string", "required": False, "description": "API path (for REST/API type)"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "get": {
                "method": "get_function",
                "params": ["agent_id", "function_id"],
                "required": ["agent_id", "function_id"],
                "description": "Get function details by ID",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "function_id": "string (required) - Unique ID for the function"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_function",
                "params": ["agent_id", "document_id", "function_id"],
                "required": ["agent_id", "document_id", "function_id"],
                "description": "Delete a function from an agent",
                "args": {
                    "agent_id": "string (required) - UUID of the agent",
                    "document_id": "string (required) - UUID of the agent's document",
                    "function_id": "string (required) - UUID of the function"
                },
                "responses": {
                    "200": "Successfully deleted",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "list": {
                "method": "list_functions",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get all functions on an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # DOCUMENT CRUD OPERATIONS
    # =========================================================================
    "document_crud": {
        "description": "List, search, delete, and upload documents on agents",
        "when_to_use": [
            "User wants to list documents on an agent",
            "User wants to search documents",
            "User wants to delete a document",
            "User wants to upload a document"
        ],
        "operations": {
            "list": {
                "method": "list_documents",
                "params": ["agent_id", "offset", "limit"],
                "required": ["agent_id"],
                "description": "Retrieve an agent's documents",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "offset": "integer (optional) - Pagination offset. Default: 0",
                    "limit": "integer (optional) - Number of results. Default: 10"
                },
                "request_body": {
                    "schema_name": "CognitiveAgentDocumentListRequestVO",
                    "fields": {
                        "offset": {"type": "integer", "required": False, "description": "Pagination offset"},
                        "limit": {"type": "integer", "required": False, "description": "Number of results"},
                        "inclFileTypeList": {"type": "array", "required": False, "description": "File types to include"},
                        "exclFileTypeList": {"type": "array", "required": False, "description": "File types to exclude"},
                        "status": {"type": "array", "required": False, "description": "Document indexing status filter"},
                        "keywords": {"type": "array", "required": False, "description": "Keywords filter"},
                        "sessionId": {"type": "string", "required": False, "description": "Session ID"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "search": {
                "method": "search_documents",
                "params": ["agent_id", "content"],
                "required": ["agent_id", "content"],
                "description": "Search for documents on an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "content": "array[string] (required) - Content search terms"
                },
                "request_body": {
                    "schema_name": "SearchDocumentRequest",
                    "fields": {
                        "content": {"type": "array", "required": True, "description": "Content search terms"},
                        "selectColumns": {"type": "string", "required": False, "description": "Columns to select"},
                        "highlight": {"type": "string", "required": False, "description": "Highlight fields"},
                        "documentsToReturnCount": {"type": "integer", "required": False, "description": "Count of documents to return"},
                        "chunkType": {"type": "string", "required": False, "description": "Chunk type (FULL, PARTIAL)"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_document",
                "params": ["agent_id", "document_id"],
                "required": ["agent_id", "document_id"],
                "description": "Delete a document from an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "document_id": "string (required) - Unique ID for Document"
                },
                "responses": {
                    "200": "Successfully deleted",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "upload": {
                "method": "upload_data",
                "params": ["agent_id", "data_upload_config"],
                "required": ["agent_id", "data_upload_config"],
                "description": "Upload and index data/document to an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "data_upload_config": "object (required) - CognitiveAgentDocumentConfig"
                },
                "request_body": {
                    "schema_name": "CognitiveAgentDocumentConfig",
                    "fields": {
                        "embeddingModel": {"type": "string", "required": False, "description": "Embedding model name"},
                        "chunkingStrategy": {"type": "string", "required": False, "description": "RECURSIVE_CHARACTER_SPLIT, TOKEN_SPLIT, PAGE_SPLIT"},
                        "tokenSplitCount": {"type": "integer", "required": False, "description": "Token count for splitting"},
                        "metadata": {"type": "object", "required": False, "description": "Custom metadata"}
                    }
                },
                "responses": {
                    "200": "Successfully created",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "upload_index": {
                "method": "upload_index_data",
                "params": ["agent_id", "data_upload_config"],
                "required": ["agent_id", "data_upload_config"],
                "description": "Upload and index data (alternative endpoint)",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "data_upload_config": "object (required) - CognitiveAgentDocumentConfig"
                },
                "request_body": {
                    "schema_name": "CognitiveAgentDocumentConfig",
                    "fields": {
                        "embeddingModel": {"type": "string", "required": False, "description": "Embedding model name"},
                        "chunkingStrategy": {"type": "string", "required": False, "description": "RECURSIVE_CHARACTER_SPLIT, TOKEN_SPLIT, PAGE_SPLIT"},
                        "tokenSplitCount": {"type": "integer", "required": False, "description": "Token count for splitting"},
                        "metadata": {"type": "object", "required": False, "description": "Custom metadata"}
                    }
                },
                "responses": {
                    "200": "Successfully created",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # IDENTITY OPERATIONS
    # =========================================================================
    "identity_operations": {
        "description": "Manage agent identity settings including avatar and credentials",
        "when_to_use": [
            "User wants to add identity to an agent",
            "User wants to configure agent avatar",
            "User wants to set agent credentials",
            "User wants to delete agent identity"
        ],
        "operations": {
            "add": {
                "method": "add_agent_identity",
                "params": ["agent_id", "identity_data"],
                "required": ["agent_id", "identity_data"],
                "description": "Add identity to an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "identity_data": "object (required) - CognitiveAgentIdentity configuration"
                },
                "request_body": {
                    "schema_name": "CognitiveAgentIdentity",
                    "fields": {
                        "displayName": {"type": "string", "required": False, "description": "Display name"},
                        "principalName": {"type": "string", "required": False, "description": "Principal name"},
                        "principalId": {"type": "string", "required": False, "description": "Principal ID"},
                        "roleCode": {"type": "string", "required": False, "description": "Role code"},
                        "avatarCharacter": {"type": "string", "required": False, "description": "Avatar character"},
                        "avatarVoice": {"type": "string", "required": False, "description": "Avatar voice"},
                        "avatarStyle": {"type": "string", "required": False, "description": "Avatar style"},
                        "avatarBackgroundColor": {"type": "string", "required": False, "description": "Avatar background color"},
                        "secretEnv": {"type": "string", "required": False, "description": "Secret environment"},
                        "secretOrgId": {"type": "string", "required": False, "description": "Secret org ID"},
                        "secretFamily": {"type": "string", "required": False, "description": "Secret family"},
                        "secretApp": {"type": "string", "required": False, "description": "Secret app"},
                        "realtimeVoice": {"type": "string", "required": False, "description": "Voice: alloy, ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_agent_identity",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Delete identity from an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully processed",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # ACCESS OPERATIONS
    # =========================================================================
    "access_operations": {
        "description": "Manage agent access control and user authorization",
        "when_to_use": [
            "User wants to grant access to an agent",
            "User wants to revoke access from an agent",
            "User wants to manage authorization settings"
        ],
        "operations": {
            "add_agent_access": {
                "method": "add_agent_access",
                "params": ["access_data"],
                "required": ["access_data"],
                "description": "Provide access to an agent",
                "args": {
                    "access_data": "object (required) - UserAuthorization containing access configuration"
                },
                "request_body": {
                    "schema_name": "UserAuthorization",
                    "fields": {
                        "userId": {"type": "string", "required": True, "description": "User ID or Group ID"},
                        "userType": {"type": "string", "required": False, "description": "User Type (COMMIT_ID, GROUP_ID)"},
                        "authType": {"type": "string", "required": False, "description": "Authorization Type"},
                        "authId": {"type": "string", "required": False, "description": "Authorization ID"},
                        "userRole": {"type": "string", "required": False, "description": "User Role (OWNER, USER)"},
                        "orgId": {"type": "string", "required": False, "description": "Organization ID"},
                        "tenantId": {"type": "string", "required": False, "description": "Tenant ID"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "remove_agent_access": {
                "method": "remove_agent_access",
                "params": ["agent_id", "user_id", "role"],
                "required": ["agent_id", "user_id", "role"],
                "description": "Remove agent access",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "user_id": "string (required) - User ID to remove access from",
                    "role": "string (required) - Role for which access is removed"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "add_auth_access": {
                "method": "add_auth_access",
                "params": ["auth_data"],
                "required": ["auth_data"],
                "description": "Provide auth access to a resource",
                "args": {
                    "auth_data": "object (required) - UserAuthorization containing access configuration"
                },
                "request_body": {
                    "schema_name": "UserAuthorization",
                    "fields": {
                        "userId": {"type": "string", "required": True, "description": "User ID or Group ID"},
                        "userType": {"type": "string", "required": False, "description": "User Type (COMMIT_ID, GROUP_ID)"},
                        "authType": {"type": "string", "required": False, "description": "Authorization Type"},
                        "authId": {"type": "string", "required": False, "description": "Authorization ID"},
                        "userRole": {"type": "string", "required": False, "description": "User Role (OWNER, USER)"},
                        "orgId": {"type": "string", "required": False, "description": "Organization ID"},
                        "tenantId": {"type": "string", "required": False, "description": "Tenant ID"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "remove_auth_access": {
                "method": "remove_auth_access",
                "params": ["agent_id", "user_id", "role"],
                "required": ["agent_id", "user_id", "role"],
                "description": "Remove auth access from a resource",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "user_id": "string (required) - User ID to remove access from",
                    "role": "string (required) - Role for which access is removed"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # IDEAS OPERATIONS
    # =========================================================================
    "ideas_operations": {
        "description": "Manage ideas and votes for agents",
        "when_to_use": [
            "User wants to view ideas for an agent",
            "User wants to vote on an idea",
            "User wants to delete an idea",
            "User wants to submit an upvote"
        ],
        "operations": {
            "get_ideas": {
                "method": "get_ideas",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get ideas for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "OK"
                }
            },
            "vote": {
                "method": "vote_idea",
                "params": ["agent_id", "idea_id"],
                "required": ["agent_id", "idea_id"],
                "description": "Upvote an idea",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "idea_id": "string (required) - Unique ID for Idea"
                },
                "responses": {
                    "200": "OK"
                }
            },
            "delete": {
                "method": "delete_idea",
                "params": ["agent_id", "idea_id"],
                "required": ["agent_id", "idea_id"],
                "description": "Delete an idea",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "idea_id": "string (required) - Unique ID for Idea"
                },
                "responses": {
                    "200": "OK"
                }
            },
            "upvote": {
                "method": "upvote",
                "params": ["vote_data"],
                "required": ["vote_data"],
                "description": "Submit an upvote",
                "args": {
                    "vote_data": "object (required) - CognitiveVote containing vote details"
                },
                "request_body": {
                    "schema_name": "CognitiveVote",
                    "fields": {
                        "cogVoteId": {"type": "string", "required": False, "description": "Vote ID"},
                        "voteCategory": {"type": "string", "required": False, "description": "Vote category"},
                        "entityKey": {"type": "string", "required": True, "description": "Entity key"},
                        "entityType": {"type": "string", "required": True, "description": "Entity type (COG_PROMPT, COG_AGENT, COG_QUESTION, COG_IDEA)"},
                        "userId": {"type": "string", "required": False, "description": "User ID"}
                    }
                },
                "responses": {
                    "200": "OK"
                }
            }
        }
    },

    # =========================================================================
    # HASHES OPERATIONS (MERKLE DAG)
    # =========================================================================
    "hashes_operations": {
        "description": "Manage Merkle DAG hashes for agents",
        "when_to_use": [
            "User wants to list hashes for an agent",
            "User wants to create a hash",
            "User wants to get current hash",
            "User wants to delete a hash"
        ],
        "operations": {
            "list": {
                "method": "list_hashes",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "List Merkle DAG hashes",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "create": {
                "method": "create_hash",
                "params": ["agent_id", "request_params"],
                "required": ["agent_id"],
                "description": "Create a Merkle DAG hash",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "request_params": "object (optional) - HashCreateRequest parameters"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "get": {
                "method": "get_hash",
                "params": ["agent_id", "include_documents"],
                "required": ["agent_id"],
                "description": "Get Merkle DAG hash",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "include_documents": "boolean (optional) - Include documents in hash"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "delete": {
                "method": "delete_hash",
                "params": ["agent_id", "hash_value"],
                "required": ["agent_id", "hash_value"],
                "description": "Delete a Merkle DAG hash",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "hash_value": "string (required) - Hash value to delete"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # INDEX OPERATIONS
    # =========================================================================
    "index_operations": {
        "description": "Search vector database indexes",
        "when_to_use": [
            "User wants to search the vector index",
            "User wants to perform semantic search",
            "User wants to search CosmosDB index"
        ],
        "operations": {
            "search": {
                "method": "search_index",
                "params": ["agent_id", "search_data"],
                "required": ["agent_id", "search_data"],
                "description": "Search vector DB index",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "search_data": "object (required) - SearchIndexRequest containing search parameters"
                },
                "request_body": {
                    "schema_name": "SearchIndexRequest",
                    "fields": {
                        "agentId": {"type": "string", "required": False, "description": "Agent ID"},
                        "whereCondition": {"type": "string", "required": False, "description": "Where condition"},
                        "metadataFilterExpression": {"type": "string", "required": False, "description": "Custom filter for metadata"},
                        "agentDocIds": {"type": "array", "required": False, "description": "Document IDs to filter"},
                        "embeddingQuery": {"type": "string", "required": True, "description": "Embedding query"},
                        "embeddingModelId": {"type": "string", "required": False, "description": "Embedding model ID"},
                        "chunkType": {"type": "string", "required": False, "description": "Chunk type (FULL, PARTIAL)"},
                        "chunksToReturn": {"type": "integer", "required": False, "description": "Number of chunks to return"},
                        "returnDocumentMetadata": {"type": "boolean", "required": False, "description": "Return document metadata"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "search_cosmosdb": {
                "method": "search_index_cosmosdb",
                "params": ["agent_id", "search_data"],
                "required": ["agent_id", "search_data"],
                "description": "Search CosmosDB vector index",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "search_data": "object (required) - SearchIndexRequest containing search parameters"
                },
                "request_body": {
                    "schema_name": "SearchIndexRequest",
                    "fields": {
                        "agentId": {"type": "string", "required": False, "description": "Agent ID"},
                        "whereCondition": {"type": "string", "required": False, "description": "Where condition"},
                        "metadataFilterExpression": {"type": "string", "required": False, "description": "Custom filter for metadata"},
                        "agentDocIds": {"type": "array", "required": False, "description": "Document IDs to filter"},
                        "embeddingQuery": {"type": "string", "required": True, "description": "Embedding query"},
                        "embeddingModelId": {"type": "string", "required": False, "description": "Embedding model ID"},
                        "chunkType": {"type": "string", "required": False, "description": "Chunk type (FULL, PARTIAL)"},
                        "chunksToReturn": {"type": "integer", "required": False, "description": "Number of chunks to return"},
                        "returnDocumentMetadata": {"type": "boolean", "required": False, "description": "Return document metadata"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # PROMOTION OPERATIONS
    # =========================================================================
    "promotion_operations": {
        "description": "Promote and import agents between environments",
        "when_to_use": [
            "User wants to promote an agent to the next environment",
            "User wants to import agent resources"
        ],
        "operations": {
            "promote": {
                "method": "promote_agent",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Promote an agent to the next environment",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully promoted",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "import": {
                "method": "import_agent",
                "params": ["import_data"],
                "required": ["import_data"],
                "description": "Import agent resources",
                "args": {
                    "import_data": "object (required) - AgentResourcesImportRequest containing import data"
                },
                "request_body": {
                    "schema_name": "AgentResourcesImportRequest",
                    "fields": {
                        "agent": {"type": "object", "required": True, "description": "Agent configuration"},
                        "nuggets": {"type": "array", "required": False, "description": "List of nuggets to import"},
                        "prompts": {"type": "array", "required": False, "description": "List of prompts to import"},
                        "functions": {"type": "array", "required": False, "description": "List of functions to import"},
                        "sourceEnvironment": {"type": "string", "required": False, "description": "Source environment"},
                        "initiatedBy": {"type": "string", "required": False, "description": "User who initiated the promotion"}
                    }
                },
                "responses": {
                    "200": "Successfully imported",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # ADVANCED OPERATIONS
    # =========================================================================
    "advanced_operations": {
        "description": "Advanced operations: back-testing, computer use, resource calls",
        "when_to_use": [
            "User wants to run back-testing for an agent",
            "User wants to use computer automation",
            "User wants to call a resource by ERN"
        ],
        "operations": {
            "back_testing": {
                "method": "back_testing",
                "params": ["agent_id", "test_data"],
                "required": ["agent_id", "test_data"],
                "description": "Run agent back-testing",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent",
                    "test_data": "object (required) - AgentBackTestingRequest configuration"
                },
                "request_body": {
                    "schema_name": "AgentBackTestingRequest",
                    "fields": {
                        "sessionId": {"type": "string", "required": False, "description": "Session ID"},
                        "baseModelId": {"type": "string", "required": True, "description": "Base Model ID"},
                        "compareModelId": {"type": "string", "required": False, "description": "Compare Model ID"},
                        "challengerModelId": {"type": "string", "required": False, "description": "Challenger Model ID"},
                        "chatRequests": {"type": "array", "required": True, "description": "Chat requests to test"}
                    }
                },
                "responses": {
                    "200": "Successfully processed",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "computer_use": {
                "method": "computer_use",
                "params": ["computer_request"],
                "required": ["computer_request"],
                "description": "Call computer use",
                "args": {
                    "computer_request": "object (required) - ComputerUseRequest configuration"
                },
                "request_body": {
                    "schema_name": "ComputerUseRequest",
                    "fields": {
                        "computerAddress": {"type": "string", "required": True, "description": "Computer address"},
                        "instruction": {"type": "string", "required": True, "description": "Instruction to execute"},
                        "systemPrompt": {"type": "string", "required": False, "description": "System prompt"}
                    }
                },
                "responses": {
                    "200": "OK"
                }
            },
            "call_resource": {
                "method": "call_resource",
                "params": ["ern_request"],
                "required": ["ern_request"],
                "description": "Call a resource by ERN",
                "args": {
                    "ern_request": "object (required) - ErnRequest containing the resource call details"
                },
                "request_body": {
                    "schema_name": "ErnRequest",
                    "fields": {
                        "ern": {"type": "string", "required": True, "description": "Eliza Resource Name (e.g., ern:eliza:agent:<agentId>)"},
                        "data": {"type": "object", "required": False, "description": "Optional data map to pass to the resource call"}
                    }
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found - Resource not found",
                    "400": "Bad Request - Invalid ERN format",
                    "500": "Internal Server Error"
                }
            }
        }
    },

    # =========================================================================
    # DISCOVERY OPERATIONS
    # =========================================================================
    "discovery_operations": {
        "description": "Discover agents by various criteria",
        "when_to_use": [
            "User wants to find agents by control flag",
            "User wants to find agents by app ID",
            "User wants to get datasource list for an agent"
        ],
        "operations": {
            "by_control_flag": {
                "method": "get_agents_by_control_flag",
                "params": ["control_flag"],
                "required": ["control_flag"],
                "description": "Get agent list for a given control flag",
                "args": {
                    "control_flag": "string (required) - Control flag to search for"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "by_app_id": {
                "method": "get_agents_by_app_id",
                "params": ["app_id"],
                "required": ["app_id"],
                "description": "Get agent list for a given app ID",
                "args": {
                    "app_id": "string (required) - App ID to search for"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            },
            "datasources": {
                "method": "get_datasource_list",
                "params": ["agent_id"],
                "required": ["agent_id"],
                "description": "Get datasource list for an agent",
                "args": {
                    "agent_id": "string (required) - Unique ID for Agent"
                },
                "responses": {
                    "200": "Successfully retrieved",
                    "404": "Not Found",
                    "400": "Bad Request",
                    "500": "Internal Server Error"
                }
            }
        }
    }
}


def get_category_names() -> list:
    """Return list of all category names."""
    return list(TOOL_REGISTRY.keys())


def get_operations_for_category(category_name: str) -> list:
    """Return list of operation names for a category."""
    category = TOOL_REGISTRY.get(category_name, {})
    return list(category.get("operations", {}).keys())


def get_operation_config(category_name: str, operation: str) -> dict:
    """Get configuration for a specific operation."""
    category = TOOL_REGISTRY.get(category_name, {})
    operations = category.get("operations", {})
    return operations.get(operation, {})


def get_when_to_use(category_name: str) -> list:
    """Get when_to_use hints for a category."""
    category = TOOL_REGISTRY.get(category_name, {})
    return category.get("when_to_use", [])
