"""
Tools module - MCP tool definitions and implementations.

TOOL ARCHITECTURE (Jan 2026):
- 7 Core tools: Agent creation, nugget workflow, documents, validation
- 6 Category tools: Communication, Integration, AI, Automation, Data, Interop
- 2 Reference tools: API endpoints, valid values
- 11 CRUD tools: Agent, nugget, and function management
- 19 Operation tools: Category-based API routing exposing 75 API endpoints

Total: 46 tools (27 original + 19 operation tools exposing 75 API endpoints)
"""

# Core tools
from tools.agents import AGENT_TOOLS, create_rag_agent, create_function_agent
from tools.nuggets import NUGGET_TOOLS, handle_search_ez_functions, handle_create_nugget
from tools.documents import DOCUMENT_TOOLS, create_document_upload
from tools.validation import VALIDATION_TOOLS, handle_validate_eliza_code, diagnose_error

# Reference tools
from tools.reference import REFERENCE_TOOLS, get_api_endpoint, get_valid_values

# Category capability tools (consolidated from 28 individual tools)
from tools.capabilities import (
    CATEGORY_TOOLS,
    handle_category_capability,
    handle_legacy_capability_tool,
    LEGACY_TOOL_MAPPING,
)

# CRUD tools for agent, nugget, and function management
from tools.crud import (
    CRUD_TOOLS,
    # Agent handlers
    handle_get_agent,
    handle_update_agent,
    handle_delete_agent,
    handle_list_agents,
    # Nugget handlers
    handle_get_nugget,
    handle_update_nugget,
    handle_delete_nugget,
    handle_list_nuggets,
    # Function handlers
    handle_get_function,
    handle_delete_function,
    handle_list_functions,
)

# Workflow orchestrator (deterministic workflow enforcement)
from tools.workflow import WORKFLOW_TOOLS, handle_eliza_workflow

# Operation tools (category-based routing to API endpoints)
from tools.operations import (
    OPERATION_TOOLS,
    CATEGORY_HANDLERS,
    # Original 7 handlers
    handle_chat_operations,
    handle_analytics_operations,
    handle_a2a_operations,
    handle_nugget_execution,
    handle_document_extended,
    handle_chunk_operations,
    handle_system_operations,
    # New 12 handlers
    handle_agent_crud,
    handle_nugget_crud,
    handle_function_crud,
    handle_document_crud,
    handle_identity_operations,
    handle_access_operations,
    handle_ideas_operations,
    handle_hashes_operations,
    handle_index_operations,
    handle_promotion_operations,
    handle_advanced_operations,
    handle_discovery_operations,
)

# Combine all tools
ALL_TOOLS = (
    WORKFLOW_TOOLS +    # 1 tool: eliza_workflow (MANDATORY orchestrator)
    AGENT_TOOLS +       # 2 tools: create_rag_agent, create_function_agent
    NUGGET_TOOLS +      # 2 tools: search_ez_functions, create_nugget
    DOCUMENT_TOOLS +    # 1 tool: create_document_upload
    VALIDATION_TOOLS +  # 2 tools: validate_eliza_code, diagnose_error
    REFERENCE_TOOLS +   # 2 tools: get_api_endpoint, get_valid_values
    CATEGORY_TOOLS +    # 6 tools: category capability tools
    CRUD_TOOLS +        # 11 tools: CRUD operations
    OPERATION_TOOLS     # 19 tools: operation category tools (75 API endpoints)
)

# Export all tool handlers
__all__ = [
    # Tool lists
    "ALL_TOOLS",
    "WORKFLOW_TOOLS",
    "AGENT_TOOLS",
    "NUGGET_TOOLS",
    "DOCUMENT_TOOLS",
    "VALIDATION_TOOLS",
    "REFERENCE_TOOLS",
    "CATEGORY_TOOLS",
    "CRUD_TOOLS",
    "OPERATION_TOOLS",
    # Workflow handler
    "handle_eliza_workflow",
    # Core handlers
    "create_rag_agent",
    "create_function_agent",
    "handle_search_ez_functions",
    "handle_create_nugget",
    "create_document_upload",
    "handle_validate_eliza_code",
    "diagnose_error",
    "get_api_endpoint",
    "get_valid_values",
    "handle_category_capability",
    "handle_legacy_capability_tool",
    "LEGACY_TOOL_MAPPING",
    # CRUD handlers
    "handle_get_agent",
    "handle_update_agent",
    "handle_delete_agent",
    "handle_list_agents",
    "handle_get_nugget",
    "handle_update_nugget",
    "handle_delete_nugget",
    "handle_list_nuggets",
    "handle_get_function",
    "handle_delete_function",
    "handle_list_functions",
    # Operation handlers (category-based API routing) - Original 7
    "CATEGORY_HANDLERS",
    "handle_chat_operations",
    "handle_analytics_operations",
    "handle_a2a_operations",
    "handle_nugget_execution",
    "handle_document_extended",
    "handle_chunk_operations",
    "handle_system_operations",
    # Operation handlers - New 12
    "handle_agent_crud",
    "handle_nugget_crud",
    "handle_function_crud",
    "handle_document_crud",
    "handle_identity_operations",
    "handle_access_operations",
    "handle_ideas_operations",
    "handle_hashes_operations",
    "handle_index_operations",
    "handle_promotion_operations",
    "handle_advanced_operations",
    "handle_discovery_operations",
]
