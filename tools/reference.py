"""
Reference Tools

MCP tools for looking up API endpoints, SDK methods, and valid values.
"""

from mcp.types import Tool
from typing import Dict, Any
import json


# Tool definitions
REFERENCE_TOOLS = [
    Tool(
        name="get_api_endpoint",
        description="""Get correct REST API endpoint format for direct Eliza API calls.

USE THIS WHEN: User needs to make direct HTTP calls to Eliza API (not SDK).

CATEGORIES:
- documents: List, search, upload documents
- agent: Create, get, delete agents
- functions: Create functions on agents
- chat: Send messages to agents
- nuggets: Create, search, execute nuggets

EXAMPLE: get_api_endpoint(category="nuggets", operation="create")""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["documents", "agent", "functions", "chat", "nuggets", "search", "sessions"],
                    "description": "API category"
                },
                "operation": {
                    "type": "string",
                    "description": "Operation: list, create, search, upload, delete, get, execute"
                }
            },
            "required": ["category", "operation"]
        }
    ),
    Tool(
        name="get_valid_values",
        description="""Get valid enum values for Eliza configuration options.

VALUE TYPES:
- control_flags: Agent control flags (ADD_KNOWLEDGE, USE_HISTORY, etc.)
- chunking_strategies: Document chunking options
- retriever_strategies: RAG retrieval strategies (STANDARD, REASON, etc.)
- models: Valid LLM model names
- function_types: Function type options (PYTHON_STATIC, REST, NUGGET)

EXAMPLE: get_valid_values(value_type="models")""",
        inputSchema={
            "type": "object",
            "properties": {
                "value_type": {
                    "type": "string",
                    "enum": ["control_flags", "chunking_strategies", "retriever_strategies", "models", "function_types"],
                    "description": "What values to get"
                }
            },
            "required": ["value_type"]
        }
    )
]


# Tool implementations
def get_api_endpoint(args: Dict[str, Any]) -> str:
    """Get API endpoint details."""
    category = args.get("category", "")
    operation = args.get("operation", "")

    endpoints = {
        "documents": {
            "list": {
                "method": "POST",
                "path": "/agents/{agent_id}/documents",
                "body": {"offset": 0, "limit": 10},
                "note": "Use offset/limit NOT pageNumber/pageSize"
            },
            "search": {
                "method": "POST",
                "path": "/agents/{agent_id}/documents/search",
                "body": {"content": ["search terms"]},
                "note": "content must be array of strings"
            },
            "upload": {
                "method": "POST",
                "path": "/agents/{agent_id}/upload-index-data",
                "note": "Multipart form data with file"
            }
        },
        "agent": {
            "create": {
                "method": "POST",
                "path": "/agents",
                "body": {"agentId": "uuid", "name": "Agent Name", "...": "..."},
                "note": "Must provide UUID as agentId, use 'name' not 'agentName'"
            },
            "get": {
                "method": "GET",
                "path": "/agents/{agent_id}"
            },
            "delete": {
                "method": "DELETE",
                "path": "/agents/{agent_id}"
            }
        },
        "functions": {
            "create": {
                "method": "POST",
                "path": "/agents/{agent_id}/functions",
                "body": {
                    "funcNameKey": "function_name",
                    "label": "Display Name",
                    "prompt": "When to use",
                    "params": [],
                    "functionType": "PYTHON_STATIC|REST|NUGGET"
                },
                "note": "Use funcNameKey not name, label not description"
            }
        },
        "chat": {
            "send": {
                "method": "POST",
                "path": "/agents/chat",
                "body": {"agentId": "...", "message": "..."}
            }
        },
        "nuggets": {
            "create": {
                "method": "POST",
                "path": "/agents/{agent_id}/nuggets/",
                "body": {"label": "...", "description": "...", "call": {"@type": "code", "language": "JavaScript", "code": "..."}}
            },
            "search": {
                "method": "POST",
                "path": "/agents/{agent_id}/nuggets/search",
                "note": "POST not GET"
            },
            "execute": {
                "method": "POST",
                "path": "/agents/{agent_id}/nuggets/{nugget_id}/call",
                "body": {"key": "value"}
            }
        }
    }

    if category in endpoints and operation in endpoints[category]:
        return json.dumps(endpoints[category][operation], indent=2)

    return f"Unknown endpoint. Available: {list(endpoints.keys())}"


def get_valid_values(args: Dict[str, Any]) -> str:
    """Get valid enum values."""
    value_type = args.get("value_type", "")

    values = {
        "control_flags": [
            "ADD_KNOWLEDGE - Add to knowledge base",
            "SESSION_DOCUMENTS - Use session documents",
            "USE_HISTORY - Include conversation history",
            "USE_MEMORY - Use agent memory",
            "RE_RANK_CHUNKS - Re-rank retrieved chunks",
            "DESCRIBE_IMAGES - Process images",
            "ENCRYPTION - Encrypt data"
        ],
        "chunking_strategies": [
            "TOKEN_SPLIT - Split by token count",
            "PAGE_SPLIT - Split by pages",
            "RECURSIVE_CHARACTER_SPLIT - Recursive text splitting (recommended)",
            "NUGGET - For nugget content"
        ],
        "retriever_strategies": [
            "STANDARD - Basic RAG, document Q&A",
            "REASON - Function calling enabled (requires openai-gpt-4.1-mini-ptu)",
            "NUGGET - Auto-run nugget on every query",
            "AVATAR - Avatar mode",
            "HYDE - Hypothetical document embeddings",
            "BM25 - BM25 retrieval"
        ],
        "models": [
            "openai-gpt-4.1-mini-ptu - Recommended for REASON strategy",
            "openai-gpt-4o - GPT-4 Omni",
            "openai-gpt-4 - GPT-4",
            "bnym-llama-3.3-70b-instruct - On-prem Llama",
            "bnym-mistral-7b-instruct - On-prem Mistral",
            "google-gemini-1.5-pro - Gemini Pro"
        ],
        "function_types": [
            "PYTHON_STATIC - Inline Python code (NO external calls)",
            "REST - HTTP API calls",
            "NUGGET - JavaScript with ez* functions (email, search, LLM)",
            "AGENT - Call another agent",
            "SQL - Database queries"
        ]
    }

    if value_type in values:
        result = f"## Valid {value_type}\n\n"
        for v in values[value_type]:
            result += f"- {v}\n"
        return result

    return f"Unknown value type. Available: {list(values.keys())}"