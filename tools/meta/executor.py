"""
Execute Tool - Meta-tool for executing any Eliza tool by name.

This tool enables the lazy loading pattern by providing a single
entry point that dispatches to the appropriate handler.

Usage:
    execute_tool(tool_name="create_nugget", arguments={...})
"""

from typing import Dict, Any
import json

from tools.hierarchy import TOOL_REGISTRY, get_all_tool_names


# Using dict format to match existing tool definitions
EXECUTE_TOOL = {
    "name": "execute_tool",
    "description": """Execute any Eliza tool by name.

WORKFLOW:
1. Use discover_tools to find the right tool
2. Use get_tool_schema to see required parameters
3. Use this tool to execute it

CONFIRMATION: For destructive operations (delete, update), the first call
returns a confirmation request. Call again with confirm_token to execute.

IMPORTANT:
- For Eliza tasks (agents, nuggets, functions), use eliza_workflow FIRST
- eliza_workflow is available directly - no need to go through execute_tool

EXAMPLE:
```
# First call - gets confirmation
execute_tool(tool_name="delete_agent", arguments={"agent_id": "..."})
# Returns: {"status": "confirmation_required", "confirm_token": "xyz", ...}

# Second call - executes with token
execute_tool(tool_name="delete_agent", confirm_token="xyz", arguments={"agent_id": "..."})
```""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to execute (from discover_tools)"
            },
            "arguments": {
                "type": "object",
                "description": "Arguments to pass to the tool (from get_tool_schema)",
                "default": {}
            },
            "confirm_token": {
                "type": "string",
                "description": "Confirmation token for destructive operations (from previous call)"
            }
        },
        "required": ["tool_name"]
    }
}


# Handler registry - populated at import time
_HANDLER_REGISTRY: Dict[str, Any] = {}


def _initialize_handlers():
    """
    Lazily initialize the handler registry.

    This imports handlers only when needed, reducing startup overhead.
    """
    global _HANDLER_REGISTRY

    if _HANDLER_REGISTRY:
        return  # Already initialized

    # Import all handlers
    # Note: This is a one-time cost when execute_tool is first called
    from tools import (
        # Workflow
        handle_eliza_workflow,
        # Agents
        create_rag_agent,
        create_function_agent,
        # Nuggets
        handle_search_ez_functions,
        handle_create_nugget,
        # Documents
        create_document_upload,
        # Validation
        handle_validate_eliza_code,
        diagnose_error,
        # Reference
        get_api_endpoint,
        get_valid_values,
        # Capabilities
        handle_category_capability,
        # CRUD
        handle_get_agent,
        handle_update_agent,
        handle_delete_agent,
        handle_list_agents,
        handle_get_nugget,
        handle_update_nugget,
        handle_delete_nugget,
        handle_list_nuggets,
        handle_get_function,
        handle_delete_function,
        handle_list_functions,
        # Operations
        handle_chat_operations,
        handle_analytics_operations,
        handle_a2a_operations,
        handle_nugget_execution,
        handle_document_extended,
        handle_chunk_operations,
        handle_system_operations,
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

    _HANDLER_REGISTRY = {
        # Workflow
        "eliza_workflow": handle_eliza_workflow,

        # Agents
        "create_rag_agent": create_rag_agent,
        "create_function_agent": create_function_agent,

        # Nuggets
        "search_ez_functions": handle_search_ez_functions,
        "create_nugget": handle_create_nugget,

        # Documents
        "create_document_upload": create_document_upload,

        # Validation
        "validate_eliza_code": handle_validate_eliza_code,
        "diagnose_error": diagnose_error,

        # Reference
        "get_api_endpoint": get_api_endpoint,
        "get_valid_values": get_valid_values,

        # Capabilities (all route through handle_category_capability)
        "create_communication_capability": lambda args: handle_category_capability("create_communication_capability", args),
        "create_integration_capability": lambda args: handle_category_capability("create_integration_capability", args),
        "create_ai_capability": lambda args: handle_category_capability("create_ai_capability", args),
        "create_automation_capability": lambda args: handle_category_capability("create_automation_capability", args),
        "create_data_capability": lambda args: handle_category_capability("create_data_capability", args),
        "create_interop_capability": lambda args: handle_category_capability("create_interop_capability", args),

        # CRUD - Agents
        "get_agent": handle_get_agent,
        "update_agent": handle_update_agent,
        "delete_agent": handle_delete_agent,
        "list_agents": handle_list_agents,

        # CRUD - Nuggets
        "get_nugget": handle_get_nugget,
        "update_nugget": handle_update_nugget,
        "delete_nugget": handle_delete_nugget,
        "list_nuggets": handle_list_nuggets,

        # CRUD - Functions
        "get_function": handle_get_function,
        "delete_function": handle_delete_function,
        "list_functions": handle_list_functions,

        # Operations
        "chat_operations": handle_chat_operations,
        "analytics_operations": handle_analytics_operations,
        "a2a_operations": handle_a2a_operations,
        "nugget_execution": handle_nugget_execution,
        "document_extended": handle_document_extended,
        "chunk_operations": handle_chunk_operations,
        "system_operations": handle_system_operations,
        "agent_crud": handle_agent_crud,
        "nugget_crud": handle_nugget_crud,
        "function_crud": handle_function_crud,
        "document_crud": handle_document_crud,
        "identity_operations": handle_identity_operations,
        "access_operations": handle_access_operations,
        "ideas_operations": handle_ideas_operations,
        "hashes_operations": handle_hashes_operations,
        "index_operations": handle_index_operations,
        "promotion_operations": handle_promotion_operations,
        "advanced_operations": handle_advanced_operations,
        "discovery_operations": handle_discovery_operations,
    }


async def handle_execute_tool(arguments: Dict[str, Any]) -> str:
    """
    Handle execute_tool requests.

    Dispatches to the appropriate handler based on tool_name.
    Passes through confirm_token for confirmation-required operations.
    """
    tool_name = arguments.get("tool_name")
    tool_args = arguments.get("arguments", {})

    # Pass through confirm_token if provided at top level
    # This allows: execute_tool(tool_name="delete_agent", confirm_token="xyz", arguments={...})
    if "confirm_token" in arguments and "confirm_token" not in tool_args:
        tool_args = {**tool_args, "confirm_token": arguments["confirm_token"]}

    if not tool_name:
        return json.dumps({
            "error": "tool_name is required",
            "hint": "Use discover_tools to find available tools"
        })

    # Check if tool exists
    if tool_name not in TOOL_REGISTRY:
        all_tools = get_all_tool_names()
        return json.dumps({
            "error": f"Unknown tool: {tool_name}",
            "hint": "Use discover_tools to find available tools",
            "available_tools_count": len(all_tools)
        })

    # Initialize handlers if needed
    _initialize_handlers()

    # Get handler
    handler = _HANDLER_REGISTRY.get(tool_name)
    if not handler:
        return json.dumps({
            "error": f"Handler not found for tool: {tool_name}",
            "hint": "This may be a configuration error. Please report this issue."
        })

    # Get tool info for async check
    tool_info = TOOL_REGISTRY.get(tool_name)

    try:
        # Execute handler (async or sync)
        if tool_info and tool_info.is_async:
            result = await handler(tool_args)
        else:
            result = handler(tool_args)

        # Format result
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        elif isinstance(result, str):
            return result
        else:
            return json.dumps({"result": str(result)})

    except Exception as e:
        return json.dumps({
            "error": f"Tool execution failed: {str(e)}",
            "tool": tool_name,
            "hint": "Check the arguments match the schema from get_tool_schema"
        })
