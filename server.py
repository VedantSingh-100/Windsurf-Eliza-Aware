#!/usr/bin/env python3
"""
Eliza MCP Server

Model Context Protocol server for generating and validating Eliza AI platform code.
Provides tools for creating agents, nuggets, functions, and more.

TOOL ARCHITECTURE (Jan 2026):
- 7 Core tools: Agent creation, nugget workflow, documents, validation
- 6 Category tools: Communication, Integration, AI, Automation, Data, Interop
- 2 Reference tools: API endpoints, valid values
- 11 CRUD tools: Agent, nugget, and function management
- 19 Operation tools: Category-based API routing exposing 75 endpoints

Total: 46 tools (27 original + 19 operation tools exposing 75 API endpoints)

Usage:
    python -m eliza_mcp.server
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from tools import (
    ALL_TOOLS,
    # Workflow orchestrator (MANDATORY for all Eliza tasks)
    handle_eliza_workflow,
    # Agent tools
    create_rag_agent,
    create_function_agent,
    # Nugget tools
    handle_search_ez_functions,
    handle_create_nugget,
    # Validation tools
    handle_validate_eliza_code,
    diagnose_error,
    # Reference tools
    get_api_endpoint,
    get_valid_values,
    # Document tools
    create_document_upload,
    # Category capability tools
    handle_category_capability,
    handle_legacy_capability_tool,
    LEGACY_TOOL_MAPPING,
    # CRUD tools
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
    # Operation tools - Original 7 (category-based API routing)
    handle_chat_operations,
    handle_analytics_operations,
    handle_a2a_operations,
    handle_nugget_execution,
    handle_document_extended,
    handle_chunk_operations,
    handle_system_operations,
    # Operation tools - New 12
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

# Create server instance
server = Server("eliza-mcp")


@server.list_tools()
async def list_tools():
    """Return all available tools."""
    return ALL_TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    # =========================================================================
    # WORKFLOW ORCHESTRATOR (1) - MANDATORY for all Eliza tasks
    # =========================================================================
    if name == "eliza_workflow":
        result = await handle_eliza_workflow(arguments)
        # Format result as markdown for readability
        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # =========================================================================
    # AGENT TOOLS (2)
    # =========================================================================
    elif name == "create_rag_agent":
        result = create_rag_agent(arguments)
    elif name == "create_function_agent":
        result = create_function_agent(arguments)

    # =========================================================================
    # NUGGET TOOLS (2)
    # =========================================================================
    elif name == "search_ez_functions":
        result = handle_search_ez_functions(arguments)
    elif name == "create_nugget":
        result = await handle_create_nugget(arguments)

    # =========================================================================
    # VALIDATION TOOLS (2)
    # =========================================================================
    elif name == "validate_eliza_code":
        result = handle_validate_eliza_code(arguments)
    elif name == "diagnose_error":
        result = diagnose_error(arguments)

    # =========================================================================
    # REFERENCE TOOLS (2)
    # =========================================================================
    elif name == "get_api_endpoint":
        result = get_api_endpoint(arguments)
    elif name == "get_valid_values":
        result = get_valid_values(arguments)

    # =========================================================================
    # DOCUMENT TOOLS (1)
    # =========================================================================
    elif name == "create_document_upload":
        result = create_document_upload(arguments)

    # =========================================================================
    # CATEGORY CAPABILITY TOOLS (6)
    # =========================================================================
    elif name == "create_communication_capability":
        result = handle_category_capability(name, arguments)
    elif name == "create_integration_capability":
        result = handle_category_capability(name, arguments)
    elif name == "create_ai_capability":
        result = handle_category_capability(name, arguments)
    elif name == "create_automation_capability":
        result = handle_category_capability(name, arguments)
    elif name == "create_data_capability":
        result = handle_category_capability(name, arguments)
    elif name == "create_interop_capability":
        result = handle_category_capability(name, arguments)

    # =========================================================================
    # LEGACY TOOL SUPPORT (backwards compatibility)
    # Old tool names (create_email_function, etc.) map to new category tools
    # =========================================================================
    elif name in LEGACY_TOOL_MAPPING:
        result = handle_legacy_capability_tool(name, arguments)

    # =========================================================================
    # CRUD TOOLS - Agent Operations (4)
    # =========================================================================
    elif name == "get_agent":
        result = handle_get_agent(arguments)
    elif name == "update_agent":
        result = handle_update_agent(arguments)
    elif name == "delete_agent":
        result = handle_delete_agent(arguments)
    elif name == "list_agents":
        result = handle_list_agents(arguments)

    # =========================================================================
    # CRUD TOOLS - Nugget Operations (4)
    # =========================================================================
    elif name == "get_nugget":
        result = handle_get_nugget(arguments)
    elif name == "update_nugget":
        result = handle_update_nugget(arguments)
    elif name == "delete_nugget":
        result = handle_delete_nugget(arguments)
    elif name == "list_nuggets":
        result = handle_list_nuggets(arguments)

    # =========================================================================
    # CRUD TOOLS - Function Operations (3)
    # =========================================================================
    elif name == "get_function":
        result = handle_get_function(arguments)
    elif name == "delete_function":
        result = handle_delete_function(arguments)
    elif name == "list_functions":
        result = handle_list_functions(arguments)

    # =========================================================================
    # OPERATION TOOLS (19) - Category-based API routing
    # These tools expose 75 API endpoints via operation parameter
    # =========================================================================
    # Original 7 operation tools
    elif name == "chat_operations":
        result = await handle_chat_operations(arguments)
    elif name == "analytics_operations":
        result = await handle_analytics_operations(arguments)
    elif name == "a2a_operations":
        result = await handle_a2a_operations(arguments)
    elif name == "nugget_execution":
        result = await handle_nugget_execution(arguments)
    elif name == "document_extended":
        result = await handle_document_extended(arguments)
    elif name == "chunk_operations":
        result = await handle_chunk_operations(arguments)
    elif name == "system_operations":
        result = await handle_system_operations(arguments)
    # New 12 operation tools
    elif name == "agent_crud":
        result = await handle_agent_crud(arguments)
    elif name == "nugget_crud":
        result = await handle_nugget_crud(arguments)
    elif name == "function_crud":
        result = await handle_function_crud(arguments)
    elif name == "document_crud":
        result = await handle_document_crud(arguments)
    elif name == "identity_operations":
        result = await handle_identity_operations(arguments)
    elif name == "access_operations":
        result = await handle_access_operations(arguments)
    elif name == "ideas_operations":
        result = await handle_ideas_operations(arguments)
    elif name == "hashes_operations":
        result = await handle_hashes_operations(arguments)
    elif name == "index_operations":
        result = await handle_index_operations(arguments)
    elif name == "promotion_operations":
        result = await handle_promotion_operations(arguments)
    elif name == "advanced_operations":
        result = await handle_advanced_operations(arguments)
    elif name == "discovery_operations":
        result = await handle_discovery_operations(arguments)

    else:
        result = f"Unknown tool: {name}. Available tools: {[t.name for t in ALL_TOOLS]}"

    return [TextContent(type="text", text=result)]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """Entry point for running the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
