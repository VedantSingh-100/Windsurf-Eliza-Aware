"""
Schema Loader - Meta-tool for getting full tool schemas on-demand.

This tool enables context-efficient discovery by allowing LLMs to
request full parameter schemas only when needed.

Usage:
    get_tool_schema(tool_name="create_nugget")
"""

from typing import Dict, Any, Optional
import json

from tools.hierarchy import TOOL_REGISTRY, get_all_tool_names


# Schema cache - populated on-demand
_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


# Using dict format to match existing tool definitions
GET_TOOL_SCHEMA = {
    "name": "get_tool_schema",
    "description": """Get the full input schema for a specific tool.

Use this after discover_tools to see the complete parameter
definition before calling execute_tool.

RETURNS:
- name: Tool name
- description: Full description with examples
- inputSchema: JSON schema with all parameters

EXAMPLE:
```
get_tool_schema(tool_name="create_nugget")
```

This returns the full schema including required fields,
types, and descriptions for each parameter.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to get schema for"
            }
        },
        "required": ["tool_name"]
    }
}


def _load_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Load the full schema for a tool.

    Imports the tool definition lazily and caches it.
    """
    if tool_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[tool_name]

    # Import tool definitions based on category
    tool_info = TOOL_REGISTRY.get(tool_name)
    if not tool_info:
        return None

    category = tool_info.category

    try:
        # Import the appropriate module and find the tool
        tool_def = None

        if category == "workflow":
            from tools.workflow import WORKFLOW_TOOLS
            tool_def = next((t for t in WORKFLOW_TOOLS if t.name == tool_name), None)

        elif category.startswith("create/agents"):
            from tools.agents import AGENT_TOOLS
            tool_def = next((t for t in AGENT_TOOLS if t.name == tool_name), None)

        elif category.startswith("create/nuggets"):
            from tools.nuggets import NUGGET_TOOLS
            tool_def = next((t for t in NUGGET_TOOLS if t.name == tool_name), None)

        elif category.startswith("create/documents"):
            from tools.documents import DOCUMENT_TOOLS
            tool_def = next((t for t in DOCUMENT_TOOLS if t.name == tool_name), None)

        elif category.startswith("create/capabilities"):
            from tools.capabilities import CATEGORY_TOOLS
            tool_def = next((t for t in CATEGORY_TOOLS if t.name == tool_name), None)

        elif category.startswith("read/"):
            from tools.crud import CRUD_TOOLS
            tool_def = next((t for t in CRUD_TOOLS if t.name == tool_name), None)

        elif category == "validation":
            from tools.validation import VALIDATION_TOOLS
            tool_def = next((t for t in VALIDATION_TOOLS if t.name == tool_name), None)

        elif category == "reference":
            from tools.reference import REFERENCE_TOOLS
            tool_def = next((t for t in REFERENCE_TOOLS if t.name == tool_name), None)

        elif category.startswith("operations/"):
            from tools.operations import OPERATION_TOOLS
            tool_def = next((t for t in OPERATION_TOOLS if t.name == tool_name), None)

        if tool_def:
            schema = {
                "name": tool_def.name,
                "description": tool_def.description,
                "inputSchema": tool_def.inputSchema
            }
            _SCHEMA_CACHE[tool_name] = schema
            return schema

    except ImportError as e:
        return {"error": f"Failed to import tool module: {e}"}

    return None


async def handle_get_tool_schema(arguments: Dict[str, Any]) -> str:
    """
    Handle get_tool_schema requests.

    Returns the full schema for a specific tool.
    """
    tool_name = arguments.get("tool_name")

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
            "hint": "Use discover_tools to search for tools",
            "available_tools_count": len(all_tools)
        })

    # Load schema
    schema = _load_tool_schema(tool_name)

    if not schema:
        return json.dumps({
            "error": f"Could not load schema for: {tool_name}",
            "hint": "This may be a configuration error"
        })

    # Add category info
    tool_info = TOOL_REGISTRY.get(tool_name)
    if tool_info:
        schema["category"] = tool_info.category
        schema["is_async"] = tool_info.is_async

    return json.dumps(schema, indent=2)


def clear_schema_cache():
    """Clear the schema cache (useful for testing)."""
    global _SCHEMA_CACHE
    _SCHEMA_CACHE = {}


def get_cached_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all cached schemas (for debugging)."""
    return _SCHEMA_CACHE.copy()
