"""
Discover Tools - Meta-tool for browsing and searching available tools.

This tool enables lazy loading by allowing LLMs to discover tools
on-demand rather than loading all 46 tool definitions upfront.

Usage:
    discover_tools(category="create/agents", detail_level="brief")
    discover_tools(search="email", detail_level="names")
"""

from typing import Dict, Any
import json

from tools.hierarchy import (
    CATEGORY_TREE,
    TOOL_REGISTRY,
    get_categories,
    get_category_info,
    get_tools_in_category,
    search_tools,
    format_tools_for_discovery,
)


# Using dict format to match existing tool definitions
DISCOVER_TOOL = {
    "name": "discover_tools",
    "description": """Discover available Eliza tools by category or search.

Use this tool FIRST to find the right tool for your task.
Then use get_tool_schema to see full parameters.
Finally use execute_tool to run the tool.

CATEGORIES:
- workflow: MANDATORY orchestrator for all Eliza tasks
- create: Create agents, nuggets, documents, capabilities
- read: Get, update, delete, list resources
- operations: Execute operations (chat, analytics, etc.)
- validation: Validate code and diagnose errors
- reference: API endpoints and valid values

SUB-CATEGORIES (use category="create/agents"):
- create/agents, create/nuggets, create/documents, create/capabilities
- read/agents, read/nuggets, read/functions
- operations/chat, operations/analytics, operations/a2a, etc.

DETAIL LEVELS:
- "names": Tool names only (minimal tokens)
- "brief": Name + one-line description (default)
- "full": Indicates to use get_tool_schema for full details

EXAMPLES:
- discover_tools() - List all categories
- discover_tools(category="create") - Tools for creating things
- discover_tools(category="create/agents") - Agent creation tools
- discover_tools(search="email") - Find email-related tools
- discover_tools(search="nugget", detail_level="names") - Minimal output""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category path (e.g., 'create', 'create/agents', 'operations/chat')"
            },
            "search": {
                "type": "string",
                "description": "Search term for tool names/descriptions"
            },
            "detail_level": {
                "type": "string",
                "enum": ["names", "brief", "full"],
                "default": "brief",
                "description": "Level of detail: names (minimal), brief (recommended), full (use get_tool_schema)"
            }
        }
    }
}


async def handle_discover_tools(arguments: Dict[str, Any]) -> str:
    """
    Handle discover_tools requests.

    Returns formatted tool discovery results based on category or search.
    """
    category = arguments.get("category")
    search_query = arguments.get("search")
    detail_level = arguments.get("detail_level", "brief")

    # If no category or search, show top-level categories
    if not category and not search_query:
        result = "## Available Tool Categories\n\n"
        for cat_name, cat_info in CATEGORY_TREE.items():
            desc = cat_info.get("description", "")
            tools_count = len(get_tools_in_category(cat_name))
            subcats = list(cat_info.get("subcategories", {}).keys())

            result += f"### {cat_name}\n"
            result += f"{desc}\n"
            result += f"Tools: {tools_count}\n"
            if subcats:
                result += f"Subcategories: {', '.join(subcats)}\n"
            result += "\n"

        result += "\n**Next steps:**\n"
        result += "- `discover_tools(category='create')` - Browse a category\n"
        result += "- `discover_tools(search='email')` - Search for tools\n"
        return result

    # Search mode
    if search_query:
        matches = search_tools(search_query)
        if not matches:
            return f"No tools found matching '{search_query}'. Try a different search term."

        result = f"## Tools matching '{search_query}'\n\n"
        tool_names = [t.name for t in matches]
        result += format_tools_for_discovery(tool_names, detail_level)

        if detail_level != "full":
            result += f"\n\n**Tip:** Use `get_tool_schema(tool_name='...')` to see full parameters."
        return result

    # Category mode
    cat_info = get_category_info(category)
    if not cat_info:
        # Suggest valid categories
        valid = get_categories()
        return f"Unknown category: '{category}'. Valid top-level categories: {', '.join(valid)}"

    result = f"## Category: {category}\n\n"
    result += f"{cat_info.get('description', '')}\n\n"

    # Show subcategories if any
    subcats = cat_info.get("subcategories", {})
    if subcats:
        result += "### Subcategories\n"
        for subcat_name, subcat_info in subcats.items():
            tools_count = len(subcat_info.get("tools", []))
            result += f"- **{category}/{subcat_name}**: {subcat_info.get('description', '')} ({tools_count} tools)\n"
        result += "\n"

    # Show tools
    tools = get_tools_in_category(category)
    if tools:
        result += "### Tools\n"
        result += format_tools_for_discovery(tools, detail_level)

    if detail_level != "full" and tools:
        result += f"\n\n**Next:** Use `get_tool_schema(tool_name='...')` to see full parameters."

    return result
