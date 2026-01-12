"""
MCP Test Client

Provides a test client for calling MCP tools directly without going through
the full MCP protocol. This allows testing the tool routing and responses.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server import call_tool


class MCPTestClient:
    """
    Test client for calling MCP tools directly.

    Bypasses the MCP protocol (stdin/stdout) and calls the tool handlers
    directly, allowing us to test routing and response content.

    Example:
        client = MCPTestClient()
        response = await client.call("search_ez_functions", {"query": "email"})
        assert "ezMail" in response
    """

    async def call(self, tool_name: str, args: dict) -> str:
        """
        Call a tool and return the text response.

        Args:
            tool_name: Name of the tool to call (e.g., "search_ez_functions")
            args: Arguments to pass to the tool

        Returns:
            The text content of the tool response
        """
        result = await call_tool(tool_name, args)
        # call_tool returns list[TextContent], extract the text
        return result[0].text if result else ""

    def call_sync(self, tool_name: str, args: dict) -> str:
        """
        Synchronous wrapper for call().

        Useful in tests that don't use async/await.
        """
        return asyncio.get_event_loop().run_until_complete(
            self.call(tool_name, args)
        )

    def assert_contains(self, response: str, *keywords: str) -> None:
        """
        Assert that response contains all the given keywords.

        Args:
            response: The tool response text
            *keywords: Keywords that should be present

        Raises:
            AssertionError: If any keyword is missing
        """
        for kw in keywords:
            assert kw in response, f"Expected '{kw}' in response:\n{response[:500]}..."

    def assert_not_contains(self, response: str, *keywords: str) -> None:
        """
        Assert that response does NOT contain any of the given keywords.

        Args:
            response: The tool response text
            *keywords: Keywords that should NOT be present

        Raises:
            AssertionError: If any keyword is found
        """
        for kw in keywords:
            assert kw not in response, f"Did NOT expect '{kw}' in response:\n{response[:500]}..."

    def assert_success(self, response: str) -> None:
        """Assert that the response indicates success (no error markers)."""
        error_markers = ["❌", "FAILED", "ERROR", "error:", "Error:"]
        for marker in error_markers:
            assert marker not in response, f"Response contains error marker '{marker}':\n{response[:500]}..."

    def assert_error(self, response: str) -> None:
        """Assert that the response indicates an error."""
        error_markers = ["❌", "FAILED", "ERROR"]
        has_error = any(marker in response for marker in error_markers)
        assert has_error, f"Expected error in response, but none found:\n{response[:500]}..."


# Convenience function for one-off calls
async def call_mcp_tool(tool_name: str, args: dict) -> str:
    """
    Convenience function to call an MCP tool.

    Args:
        tool_name: Name of the tool
        args: Tool arguments

    Returns:
        Tool response text
    """
    client = MCPTestClient()
    return await client.call(tool_name, args)
