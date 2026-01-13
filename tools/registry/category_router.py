"""
Category Router - Generic tool generation and dispatch with RICH documentation.

HYBRID APPROACH (Jan 2026):
This module implements a hybrid documentation strategy:
1. PRIMARY: Extract docstrings from ElizaClient methods at runtime (always current)
2. FALLBACK: Use full schemas from TOOL_REGISTRY (version-controlled backup)
3. VALIDATION: Schema validator can compare both sources for drift detection

This ensures Windsurf sees RICH documentation including:
- Full parameter descriptions (Args)
- Request body schemas with all fields
- Response codes and meanings
- "When to use" hints for tool selection

All category tools are STANDALONE - they don't go through eliza_workflow.
They use credentials from the workflow state if available.
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from mcp.types import Tool

from tools.registry.tool_registry import (
    TOOL_REGISTRY,
    PARAM_SCHEMAS,
    get_operation_config,
    get_when_to_use,
)
from tools.registry.docstring_extractor import (
    extract_method_docs,
    format_docs_for_description,
)
from api.client import get_client


def get_credentials_from_state(workspace_path: str = None) -> Tuple[Optional[str], str]:
    """
    Get JWT token and environment from workflow state.

    Returns:
        Tuple of (jwt_token, env) - jwt_token may be None if not set
    """
    if workspace_path is None:
        workspace_path = os.getcwd()

    state_dir = os.path.join(workspace_path, ".eliza")
    state_file = os.path.join(state_dir, "workflow_state.json")

    if not os.path.exists(state_file):
        return None, "QA"

    try:
        with open(state_file, "r") as f:
            state = json.load(f)

        # Handle both v1.0 and v2.0 state formats
        if state.get("version") == "2.0":
            credentials = state.get("credentials", {})
        else:
            credentials = state

        jwt_token = credentials.get("jwt_token")
        env = credentials.get("env", "QA")

        return jwt_token, env
    except (json.JSONDecodeError, IOError):
        return None, "QA"


def get_all_params_schema(category: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build JSON Schema properties for all possible parameters in a category.

    Args:
        category: Category definition from TOOL_REGISTRY

    Returns:
        Dict of parameter schemas for inputSchema properties
    """
    all_params = set()

    # Collect all unique parameters from all operations
    for op_config in category.get("operations", {}).values():
        for param in op_config.get("params", []):
            all_params.add(param)

    # Build schema dict
    properties = {}
    for param in all_params:
        if param in PARAM_SCHEMAS:
            properties[param] = PARAM_SCHEMAS[param]
        else:
            # Default schema for unknown params
            properties[param] = {
                "type": "string",
                "description": f"Parameter: {param}"
            }

    return properties


def build_docs_from_registry(op_config: Dict[str, Any]) -> str:
    """
    Build documentation string from registry schema (fallback).

    Used when docstring extraction fails or returns empty.

    Args:
        op_config: Operation configuration from TOOL_REGISTRY

    Returns:
        Formatted documentation string
    """
    parts = []

    # Args section
    if op_config.get("args"):
        args_lines = ["Args:"]
        for param_name, param_desc in op_config["args"].items():
            args_lines.append(f"    {param_name}: {param_desc}")
        parts.append("\n".join(args_lines))

    # Request Body section
    if op_config.get("request_body"):
        rb = op_config["request_body"]
        rb_lines = [f"Request Body ({rb.get('schema_name', 'object')}):"]
        for field_name, field_meta in rb.get("fields", {}).items():
            req_marker = "(required)" if field_meta.get("required") else ""
            rb_lines.append(
                f"    - {field_name}: {field_meta['type']} {req_marker} - {field_meta['description']}"
            )
        parts.append("\n".join(rb_lines))

    # Responses section
    if op_config.get("responses"):
        resp_lines = ["Responses:"]
        for code, desc in op_config["responses"].items():
            resp_lines.append(f"    - {code}: {desc}")
        parts.append("\n".join(resp_lines))

    return "\n\n".join(parts)


def build_rich_input_schema(category: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build JSON Schema with $defs for complex types.

    This creates a richer schema that includes definitions for
    request body types, making it easier for Windsurf to understand
    the expected structure.

    Args:
        category: Category definition from TOOL_REGISTRY

    Returns:
        JSON Schema dict with properties and $defs
    """
    operations = list(category["operations"].keys())

    # Base properties
    properties = {
        "operation": {
            "type": "string",
            "enum": operations,
            "description": f"Operation to perform: {', '.join(operations)}"
        }
    }

    # Add all possible parameter schemas with descriptions
    properties.update(get_all_params_schema(category))

    # Collect complex type definitions from request_body schemas
    definitions = {}
    for op_name, op_config in category.get("operations", {}).items():
        if op_config.get("request_body"):
            rb = op_config["request_body"]
            schema_name = rb.get("schema_name", f"{op_name}Request")

            # Build properties for the schema
            schema_properties = {}
            required_fields = []

            for field_name, field_meta in rb.get("fields", {}).items():
                schema_properties[field_name] = {
                    "type": field_meta.get("type", "string"),
                    "description": field_meta.get("description", "")
                }
                if field_meta.get("required"):
                    required_fields.append(field_name)

            definitions[schema_name] = {
                "type": "object",
                "description": f"Request body for {op_config.get('method', op_name)}",
                "properties": schema_properties,
            }
            if required_fields:
                definitions[schema_name]["required"] = required_fields

    # Build final schema
    schema = {
        "type": "object",
        "properties": properties,
        "required": ["operation"]
    }

    # Add $defs only if we have definitions
    if definitions:
        schema["$defs"] = definitions

    return schema


def create_category_tool(category_name: str) -> Tool:
    """
    Generate MCP Tool definition for a category with RICH documentation.

    HYBRID APPROACH:
    1. PRIMARY: Extract docstrings from ElizaClient methods (always current)
    2. FALLBACK: Use schemas from TOOL_REGISTRY (version-controlled backup)

    This ensures Windsurf receives comprehensive documentation including:
    - Category description and when_to_use hints
    - For each operation: full Args, Request Body schema, Response codes

    Args:
        category_name: Name of the category in TOOL_REGISTRY

    Returns:
        mcp.types.Tool instance with rich description ready for registration
    """
    category = TOOL_REGISTRY.get(category_name)
    if not category:
        raise ValueError(f"Unknown category: {category_name}")

    # Build RICH description for each operation
    operation_docs = []

    for op_name, op_config in category["operations"].items():
        method_name = op_config.get("method", op_name)
        required = op_config.get("required", [])

        # PRIMARY: Extract from client.py docstring
        method_docs = extract_method_docs(method_name)
        docstring_content = format_docs_for_description(method_docs)

        # FALLBACK: Use registry schema if docstring is empty
        if not docstring_content.strip():
            docstring_content = build_docs_from_registry(op_config)

        # Build operation documentation block
        op_desc = op_config.get("description", method_name)
        required_str = f"**Required:** {', '.join(required)}" if required else ""

        op_doc = f"""
### {op_name}
{op_desc}
{required_str}

{docstring_content}
"""
        operation_docs.append(op_doc)

    # Get "when_to_use" hints for discoverability
    when_to_use = get_when_to_use(category_name)
    when_to_use_section = ""
    if when_to_use:
        hints = "\n".join([f"- {hint}" for hint in when_to_use])
        when_to_use_section = f"""
## When to Use This Tool
{hints}
"""

    # Build full description
    full_description = f"""{category['description']}
{when_to_use_section}
## Available Operations
{''.join(operation_docs)}
"""

    # Build rich input schema with $defs for complex types
    input_schema = build_rich_input_schema(category)

    return Tool(
        name=category_name,
        description=full_description,
        inputSchema=input_schema
    )


async def handle_category_operation(
    category_name: str,
    arguments: Dict[str, Any],
    workspace_path: str = None
) -> str:
    """
    Generic handler for any category operation.

    Args:
        category_name: Name of the category (e.g., "chat_operations")
        arguments: Tool arguments including "operation" and params
        workspace_path: Path to workspace for credential lookup

    Returns:
        JSON string with operation result
    """
    operation = arguments.get("operation")
    if not operation:
        return json.dumps({
            "error": "Missing required parameter: operation",
            "fix": f"Specify one of the available operations for {category_name}"
        })

    # Get operation configuration
    category = TOOL_REGISTRY.get(category_name)
    if not category:
        return json.dumps({
            "error": f"Unknown category: {category_name}",
            "fix": "Use a valid category name from the registry"
        })

    op_config = category["operations"].get(operation)
    if not op_config:
        available = list(category["operations"].keys())
        return json.dumps({
            "error": f"Unknown operation: {operation}",
            "available_operations": available,
            "fix": f"Use one of: {', '.join(available)}"
        })

    # Validate required parameters
    missing_params = []
    for param in op_config.get("required", []):
        if param not in arguments or arguments[param] is None:
            missing_params.append(param)

    if missing_params:
        return json.dumps({
            "error": f"Missing required parameters: {', '.join(missing_params)}",
            "operation": operation,
            "fix": f"Provide values for: {', '.join(missing_params)}"
        })

    # Get credentials from workflow state
    jwt_token, env = get_credentials_from_state(workspace_path)

    # Allow override from arguments
    jwt_token = arguments.get("jwt_token", jwt_token)
    env = arguments.get("env", env)

    if not jwt_token:
        return json.dumps({
            "error": "No JWT token available",
            "fix": "Run eliza_workflow(action='start') first to provide credentials, or pass jwt_token in arguments"
        })

    # Create client and get method
    try:
        client = get_client(jwt_token, env)
        method = getattr(client, op_config["method"], None)

        if not method:
            return json.dumps({
                "error": f"Method not found: {op_config['method']}",
                "fix": "This is an internal error - the method mapping is incorrect"
            })

        # Build method arguments in order
        method_args = []
        method_kwargs = {}

        for param in op_config.get("params", []):
            value = arguments.get(param)
            if value is not None:
                method_args.append(value)
            elif param in op_config.get("required", []):
                # This shouldn't happen due to earlier validation
                pass
            else:
                # Optional param not provided - use None for positional, skip for kwargs
                method_args.append(None)

        # Remove trailing None values
        while method_args and method_args[-1] is None:
            method_args.pop()

        # Call the method
        success, result = method(*method_args)

        return json.dumps({
            "success": success,
            "operation": operation,
            "result": result
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "error": f"Operation failed: {str(e)}",
            "operation": operation,
            "fix": "Check the error details and try again"
        })


def get_all_category_tools() -> List[Tool]:
    """
    Generate Tool definitions for all categories in the registry.

    Returns:
        List of mcp.types.Tool instances
    """
    tools = []
    for category_name in TOOL_REGISTRY.keys():
        tools.append(create_category_tool(category_name))
    return tools


# Pre-generate tools for export
OPERATION_TOOLS = get_all_category_tools()


# Individual handlers for each category (for explicit routing in server.py)
async def handle_chat_operations(arguments: Dict[str, Any]) -> str:
    """Handle chat_operations tool calls."""
    return await handle_category_operation("chat_operations", arguments)


async def handle_analytics_operations(arguments: Dict[str, Any]) -> str:
    """Handle analytics_operations tool calls."""
    return await handle_category_operation("analytics_operations", arguments)


async def handle_a2a_operations(arguments: Dict[str, Any]) -> str:
    """Handle a2a_operations tool calls."""
    return await handle_category_operation("a2a_operations", arguments)


async def handle_nugget_execution(arguments: Dict[str, Any]) -> str:
    """Handle nugget_execution tool calls."""
    return await handle_category_operation("nugget_execution", arguments)


async def handle_document_extended(arguments: Dict[str, Any]) -> str:
    """Handle document_extended tool calls."""
    return await handle_category_operation("document_extended", arguments)


async def handle_chunk_operations(arguments: Dict[str, Any]) -> str:
    """Handle chunk_operations tool calls."""
    return await handle_category_operation("chunk_operations", arguments)


async def handle_system_operations(arguments: Dict[str, Any]) -> str:
    """Handle system_operations tool calls."""
    return await handle_category_operation("system_operations", arguments)


# =========================================================================
# NEW CATEGORY HANDLERS (12) - Added for full coverage
# =========================================================================

async def handle_agent_crud(arguments: Dict[str, Any]) -> str:
    """Handle agent_crud tool calls."""
    return await handle_category_operation("agent_crud", arguments)


async def handle_nugget_crud(arguments: Dict[str, Any]) -> str:
    """Handle nugget_crud tool calls."""
    return await handle_category_operation("nugget_crud", arguments)


async def handle_function_crud(arguments: Dict[str, Any]) -> str:
    """Handle function_crud tool calls."""
    return await handle_category_operation("function_crud", arguments)


async def handle_document_crud(arguments: Dict[str, Any]) -> str:
    """Handle document_crud tool calls."""
    return await handle_category_operation("document_crud", arguments)


async def handle_identity_operations(arguments: Dict[str, Any]) -> str:
    """Handle identity_operations tool calls."""
    return await handle_category_operation("identity_operations", arguments)


async def handle_access_operations(arguments: Dict[str, Any]) -> str:
    """Handle access_operations tool calls."""
    return await handle_category_operation("access_operations", arguments)


async def handle_ideas_operations(arguments: Dict[str, Any]) -> str:
    """Handle ideas_operations tool calls."""
    return await handle_category_operation("ideas_operations", arguments)


async def handle_hashes_operations(arguments: Dict[str, Any]) -> str:
    """Handle hashes_operations tool calls."""
    return await handle_category_operation("hashes_operations", arguments)


async def handle_index_operations(arguments: Dict[str, Any]) -> str:
    """Handle index_operations tool calls."""
    return await handle_category_operation("index_operations", arguments)


async def handle_promotion_operations(arguments: Dict[str, Any]) -> str:
    """Handle promotion_operations tool calls."""
    return await handle_category_operation("promotion_operations", arguments)


async def handle_advanced_operations(arguments: Dict[str, Any]) -> str:
    """Handle advanced_operations tool calls."""
    return await handle_category_operation("advanced_operations", arguments)


async def handle_discovery_operations(arguments: Dict[str, Any]) -> str:
    """Handle discovery_operations tool calls."""
    return await handle_category_operation("discovery_operations", arguments)


# Map category names to handlers for server.py routing (all 19 categories)
CATEGORY_HANDLERS = {
    # Original 7 operation tools
    "chat_operations": handle_chat_operations,
    "analytics_operations": handle_analytics_operations,
    "a2a_operations": handle_a2a_operations,
    "nugget_execution": handle_nugget_execution,
    "document_extended": handle_document_extended,
    "chunk_operations": handle_chunk_operations,
    "system_operations": handle_system_operations,
    # New 12 operation tools
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
