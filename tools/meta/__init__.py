"""
Meta-tools module for lazy discovery pattern.

Provides 3 meta-tools that reduce context load by ~87%:
1. discover_tools - Browse/search tools by category
2. execute_tool - Execute any tool by name
3. get_tool_schema - Get full schema on-demand

The eliza_workflow tool remains always visible as the 4th tool.

Usage:
    from tools.meta import META_TOOLS, META_HANDLERS
"""

from tools.meta.discover import (
    DISCOVER_TOOL,
    handle_discover_tools,
)
from tools.meta.executor import (
    EXECUTE_TOOL,
    handle_execute_tool,
)
from tools.meta.schema_loader import (
    GET_TOOL_SCHEMA,
    handle_get_tool_schema,
)

# All meta-tools (excluding eliza_workflow which is always visible)
# Using list format to match existing tool definitions
META_TOOLS = [
    DISCOVER_TOOL,
    EXECUTE_TOOL,
    GET_TOOL_SCHEMA,
]

# Handler mapping for server.py
META_HANDLERS = {
    "discover_tools": handle_discover_tools,
    "execute_tool": handle_execute_tool,
    "get_tool_schema": handle_get_tool_schema,
}

__all__ = [
    "META_TOOLS",
    "META_HANDLERS",
    "DISCOVER_TOOL",
    "EXECUTE_TOOL",
    "GET_TOOL_SCHEMA",
    "handle_discover_tools",
    "handle_execute_tool",
    "handle_get_tool_schema",
]
