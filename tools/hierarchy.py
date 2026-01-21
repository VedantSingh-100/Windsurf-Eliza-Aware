"""
Tool Hierarchy Definition

Defines the category tree structure for the lazy discovery pattern.
Maps all 46 tools to their categories with brief descriptions for
context-efficient discovery.

ARCHITECTURE (Jan 2026):
- 6 top-level categories: workflow, create, read, operations, validation, reference
- Tools are referenced by name, handlers loaded on-demand
- brief_description is used for "brief" detail level (one-line)
- Full descriptions stay in original tool definitions
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class ToolInfo:
    """Minimal tool metadata for discovery."""
    name: str
    brief: str  # One-line description for "brief" detail level
    category: str  # Full category path (e.g., "create/agents")
    is_async: bool = False  # Whether handler is async


# =============================================================================
# TOOL CATEGORY HIERARCHY
# =============================================================================

CATEGORY_TREE: Dict[str, Any] = {
    "workflow": {
        "description": "Workflow orchestration (MANDATORY for all Eliza tasks)",
        "subcategories": {},
        "tools": ["eliza_workflow"]
    },
    "create": {
        "description": "Create new agents, nuggets, documents, and capabilities",
        "subcategories": {
            "agents": {
                "description": "Create RAG and function-based agents",
                "tools": ["create_rag_agent", "create_function_agent"]
            },
            "nuggets": {
                "description": "Create and search for nuggets",
                "tools": ["search_ez_functions", "create_nugget"]
            },
            "documents": {
                "description": "Upload documents to agents",
                "tools": ["create_document_upload"]
            },
            "capabilities": {
                "description": "Add capability functions to agents",
                "tools": [
                    "create_communication_capability",
                    "create_integration_capability",
                    "create_ai_capability",
                    "create_automation_capability",
                    "create_data_capability",
                    "create_interop_capability"
                ]
            }
        },
        "tools": []  # Tools at this level (none - all in subcategories)
    },
    "read": {
        "description": "Read, update, delete, and list existing resources",
        "subcategories": {
            "agents": {
                "description": "Agent CRUD operations",
                "tools": ["get_agent", "update_agent", "delete_agent", "list_agents"]
            },
            "nuggets": {
                "description": "Nugget CRUD operations",
                "tools": ["get_nugget", "update_nugget", "delete_nugget", "list_nuggets"]
            },
            "functions": {
                "description": "Function management",
                "tools": ["get_function", "delete_function", "list_functions"]
            }
        },
        "tools": []
    },
    "operations": {
        "description": "Execute operations on existing resources (75 API endpoints)",
        "subcategories": {
            "chat": {
                "description": "Chat and query agents",
                "tools": ["chat_operations"]
            },
            "analytics": {
                "description": "Usage analytics and history",
                "tools": ["analytics_operations"]
            },
            "a2a": {
                "description": "Agent-to-agent communication",
                "tools": ["a2a_operations"]
            },
            "nugget_exec": {
                "description": "Execute existing nuggets",
                "tools": ["nugget_execution"]
            },
            "documents": {
                "description": "Document operations",
                "tools": ["document_extended", "document_crud"]
            },
            "chunks": {
                "description": "Chunk management",
                "tools": ["chunk_operations"]
            },
            "system": {
                "description": "System information",
                "tools": ["system_operations"]
            },
            "identity": {
                "description": "Agent identity management",
                "tools": ["identity_operations"]
            },
            "access": {
                "description": "Access control",
                "tools": ["access_operations"]
            },
            "ideas": {
                "description": "Ideas and voting",
                "tools": ["ideas_operations"]
            },
            "hashes": {
                "description": "Merkle DAG hashes",
                "tools": ["hashes_operations"]
            },
            "index": {
                "description": "Vector index search",
                "tools": ["index_operations"]
            },
            "promotion": {
                "description": "Agent promotion and import",
                "tools": ["promotion_operations"]
            },
            "advanced": {
                "description": "Advanced features (back-testing, computer use)",
                "tools": ["advanced_operations"]
            },
            "discovery": {
                "description": "Agent discovery",
                "tools": ["discovery_operations"]
            },
            "crud": {
                "description": "CRUD via operation tools",
                "tools": ["agent_crud", "nugget_crud", "function_crud"]
            }
        },
        "tools": []
    },
    "validation": {
        "description": "Validate code and diagnose errors",
        "subcategories": {},
        "tools": ["validate_eliza_code", "diagnose_error"]
    },
    "reference": {
        "description": "Reference information (API endpoints, valid values)",
        "subcategories": {},
        "tools": ["get_api_endpoint", "get_valid_values"]
    }
}


# =============================================================================
# TOOL REGISTRY - Maps tool names to metadata
# =============================================================================

TOOL_REGISTRY: Dict[str, ToolInfo] = {
    # Workflow (1 tool)
    "eliza_workflow": ToolInfo(
        name="eliza_workflow",
        brief="MANDATORY orchestrator for all Eliza tasks (start, continue, retry, reset)",
        category="workflow",
        is_async=True
    ),

    # Create - Agents (2 tools)
    "create_rag_agent": ToolInfo(
        name="create_rag_agent",
        brief="Create a RAG (Retrieval-Augmented Generation) agent",
        category="create/agents",
        is_async=False
    ),
    "create_function_agent": ToolInfo(
        name="create_function_agent",
        brief="Create a function-based agent",
        category="create/agents",
        is_async=False
    ),

    # Create - Nuggets (2 tools)
    "search_ez_functions": ToolInfo(
        name="search_ez_functions",
        brief="Search for ez* functions by keyword (ezMail, ezApi, etc.)",
        category="create/nuggets",
        is_async=False
    ),
    "create_nugget": ToolInfo(
        name="create_nugget",
        brief="Create and validate a JavaScript nugget on an agent",
        category="create/nuggets",
        is_async=True
    ),

    # Create - Documents (1 tool)
    "create_document_upload": ToolInfo(
        name="create_document_upload",
        brief="Upload a document to an agent for RAG",
        category="create/documents",
        is_async=False
    ),

    # Create - Capabilities (6 tools)
    "create_communication_capability": ToolInfo(
        name="create_communication_capability",
        brief="Add email, notification, chat, or Teams/Slack capability",
        category="create/capabilities",
        is_async=False
    ),
    "create_integration_capability": ToolInfo(
        name="create_integration_capability",
        brief="Add API, webhook, database, or file system integration",
        category="create/capabilities",
        is_async=False
    ),
    "create_ai_capability": ToolInfo(
        name="create_ai_capability",
        brief="Add AI/ML capabilities (sentiment, NER, summarization)",
        category="create/capabilities",
        is_async=False
    ),
    "create_automation_capability": ToolInfo(
        name="create_automation_capability",
        brief="Add scheduling, triggers, or workflow automation",
        category="create/capabilities",
        is_async=False
    ),
    "create_data_capability": ToolInfo(
        name="create_data_capability",
        brief="Add data transformation, validation, or aggregation",
        category="create/capabilities",
        is_async=False
    ),
    "create_interop_capability": ToolInfo(
        name="create_interop_capability",
        brief="Add cross-system integration (CRM, ERP, etc.)",
        category="create/capabilities",
        is_async=False
    ),

    # Read - Agents (4 tools)
    "get_agent": ToolInfo(
        name="get_agent",
        brief="Get details of a specific agent by ID",
        category="read/agents",
        is_async=False
    ),
    "update_agent": ToolInfo(
        name="update_agent",
        brief="Update an agent's configuration",
        category="read/agents",
        is_async=False
    ),
    "delete_agent": ToolInfo(
        name="delete_agent",
        brief="Delete an agent by ID",
        category="read/agents",
        is_async=False
    ),
    "list_agents": ToolInfo(
        name="list_agents",
        brief="List all agents (optionally filter by status)",
        category="read/agents",
        is_async=False
    ),

    # Read - Nuggets (4 tools)
    "get_nugget": ToolInfo(
        name="get_nugget",
        brief="Get details of a specific nugget by ID",
        category="read/nuggets",
        is_async=False
    ),
    "update_nugget": ToolInfo(
        name="update_nugget",
        brief="Update a nugget's configuration",
        category="read/nuggets",
        is_async=False
    ),
    "delete_nugget": ToolInfo(
        name="delete_nugget",
        brief="Delete a nugget by ID",
        category="read/nuggets",
        is_async=False
    ),
    "list_nuggets": ToolInfo(
        name="list_nuggets",
        brief="List all nuggets for an agent",
        category="read/nuggets",
        is_async=False
    ),

    # Read - Functions (3 tools)
    "get_function": ToolInfo(
        name="get_function",
        brief="Get details of a specific function",
        category="read/functions",
        is_async=False
    ),
    "delete_function": ToolInfo(
        name="delete_function",
        brief="Delete a function from an agent",
        category="read/functions",
        is_async=False
    ),
    "list_functions": ToolInfo(
        name="list_functions",
        brief="List all functions for an agent",
        category="read/functions",
        is_async=False
    ),

    # Validation (2 tools)
    "validate_eliza_code": ToolInfo(
        name="validate_eliza_code",
        brief="Validate Python or JavaScript code syntax and patterns",
        category="validation",
        is_async=False
    ),
    "diagnose_error": ToolInfo(
        name="diagnose_error",
        brief="Diagnose common Eliza errors and suggest fixes",
        category="validation",
        is_async=False
    ),

    # Reference (2 tools)
    "get_api_endpoint": ToolInfo(
        name="get_api_endpoint",
        brief="Get API endpoint details for Eliza operations",
        category="reference",
        is_async=False
    ),
    "get_valid_values": ToolInfo(
        name="get_valid_values",
        brief="Get valid values for configuration fields",
        category="reference",
        is_async=False
    ),

    # Operations - Original 7
    "chat_operations": ToolInfo(
        name="chat_operations",
        brief="Chat with agents: chat, query, bulk, bulk_extended",
        category="operations/chat",
        is_async=True
    ),
    "analytics_operations": ToolInfo(
        name="analytics_operations",
        brief="Analytics: activity, users, analytics, history, top_questions",
        category="operations/analytics",
        is_async=True
    ),
    "a2a_operations": ToolInfo(
        name="a2a_operations",
        brief="A2A: register, register_to_agent, list, delete",
        category="operations/a2a",
        is_async=True
    ),
    "nugget_execution": ToolInfo(
        name="nugget_execution",
        brief="Execute nuggets: call, call_dynamic, call_bulk, search",
        category="operations/nugget_exec",
        is_async=True
    ),
    "document_extended": ToolInfo(
        name="document_extended",
        brief="Docs: get, download, metadata, reindex",
        category="operations/documents",
        is_async=True
    ),
    "chunk_operations": ToolInfo(
        name="chunk_operations",
        brief="Chunks: update, delete, create_virtual",
        category="operations/chunks",
        is_async=True
    ),
    "system_operations": ToolInfo(
        name="system_operations",
        brief="System: get_models, chunking_strategies, agent_users, initiatives",
        category="operations/system",
        is_async=True
    ),

    # Operations - New 12
    "agent_crud": ToolInfo(
        name="agent_crud",
        brief="Agent CRUD via API: create, get, update, delete, list, disable",
        category="operations/crud",
        is_async=True
    ),
    "nugget_crud": ToolInfo(
        name="nugget_crud",
        brief="Nugget CRUD via API: create, get, update, delete",
        category="operations/crud",
        is_async=True
    ),
    "function_crud": ToolInfo(
        name="function_crud",
        brief="Function CRUD via API: add, get, delete, list",
        category="operations/crud",
        is_async=True
    ),
    "document_crud": ToolInfo(
        name="document_crud",
        brief="Document CRUD: list, search, delete, upload, upload_index",
        category="operations/documents",
        is_async=True
    ),
    "identity_operations": ToolInfo(
        name="identity_operations",
        brief="Identity: add, delete agent identities",
        category="operations/identity",
        is_async=True
    ),
    "access_operations": ToolInfo(
        name="access_operations",
        brief="Access: add/remove agent access, auth access",
        category="operations/access",
        is_async=True
    ),
    "ideas_operations": ToolInfo(
        name="ideas_operations",
        brief="Ideas: get_ideas, vote, delete, upvote",
        category="operations/ideas",
        is_async=True
    ),
    "hashes_operations": ToolInfo(
        name="hashes_operations",
        brief="Hashes: list, create, get, delete Merkle DAG hashes",
        category="operations/hashes",
        is_async=True
    ),
    "index_operations": ToolInfo(
        name="index_operations",
        brief="Index: search, search_cosmosdb vector indexes",
        category="operations/index",
        is_async=True
    ),
    "promotion_operations": ToolInfo(
        name="promotion_operations",
        brief="Promotion: promote, import agents across environments",
        category="operations/promotion",
        is_async=True
    ),
    "advanced_operations": ToolInfo(
        name="advanced_operations",
        brief="Advanced: back_testing, computer_use, call_resource",
        category="operations/advanced",
        is_async=True
    ),
    "discovery_operations": ToolInfo(
        name="discovery_operations",
        brief="Discovery: by_control_flag, by_app_id, datasources",
        category="operations/discovery",
        is_async=True
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_categories() -> List[str]:
    """Get list of top-level categories."""
    return list(CATEGORY_TREE.keys())


def get_category_info(category_path: str) -> Optional[Dict[str, Any]]:
    """
    Get category information by path.

    Args:
        category_path: Category path like "create" or "create/agents"

    Returns:
        Category dict with description, subcategories, and tools
    """
    parts = category_path.split("/")
    current = CATEGORY_TREE

    for part in parts:
        if part in current:
            current = current[part]
        elif "subcategories" in current and part in current["subcategories"]:
            current = current["subcategories"][part]
        else:
            return None

    return current


def get_tools_in_category(category_path: str) -> List[str]:
    """
    Get all tools in a category (including subcategories).

    Args:
        category_path: Category path like "create" or "create/agents"

    Returns:
        List of tool names
    """
    category = get_category_info(category_path)
    if not category:
        return []

    tools = list(category.get("tools", []))

    # Recursively get tools from subcategories
    for subcat_name, subcat in category.get("subcategories", {}).items():
        tools.extend(subcat.get("tools", []))
        # Only one level deep for now

    return tools


def get_tool_info(tool_name: str) -> Optional[ToolInfo]:
    """Get tool info by name."""
    return TOOL_REGISTRY.get(tool_name)


def search_tools(query: str) -> List[ToolInfo]:
    """
    Search for tools by name or description.

    Args:
        query: Search query (case-insensitive)

    Returns:
        List of matching ToolInfo objects
    """
    query_lower = query.lower()
    results = []

    for tool_info in TOOL_REGISTRY.values():
        if (query_lower in tool_info.name.lower() or
            query_lower in tool_info.brief.lower() or
            query_lower in tool_info.category.lower()):
            results.append(tool_info)

    return results


def get_all_tool_names() -> List[str]:
    """Get list of all tool names."""
    return list(TOOL_REGISTRY.keys())


def format_tools_for_discovery(
    tools: List[str],
    detail_level: str = "brief"
) -> str:
    """
    Format tools for discovery response.

    Args:
        tools: List of tool names
        detail_level: "names", "brief", or "full"

    Returns:
        Formatted string for response
    """
    if detail_level == "names":
        return "\n".join(f"- {name}" for name in tools)

    elif detail_level == "brief":
        lines = []
        for name in tools:
            info = TOOL_REGISTRY.get(name)
            if info:
                lines.append(f"- **{name}**: {info.brief}")
            else:
                lines.append(f"- {name}")
        return "\n".join(lines)

    else:  # "full" - will be handled by schema_loader
        return "\n".join(f"- {name} (use get_tool_schema for full details)" for name in tools)
