"""
Response Parser

Utilities for parsing MCP tool responses to extract:
- Code blocks
- File paths
- Nugget/function IDs
- Status information
"""

import re
from typing import Optional


def extract_code_blocks(response: str, language: Optional[str] = None) -> list[str]:
    """
    Extract all code blocks from an MCP response.

    Args:
        response: The tool response text
        language: Optional language filter (e.g., "javascript", "python")

    Returns:
        List of code block contents
    """
    if language:
        pattern = rf"```{language}\n(.*?)```"
    else:
        pattern = r"```(?:\w+)?\n(.*?)```"

    return re.findall(pattern, response, re.DOTALL)


def extract_javascript_code(response: str) -> Optional[str]:
    """
    Extract the first JavaScript code block from a response.

    Returns:
        JavaScript code or None if not found
    """
    blocks = extract_code_blocks(response, "javascript")
    if not blocks:
        blocks = extract_code_blocks(response, "js")
    return blocks[0] if blocks else None


def extract_file_path(response: str, marker: str = "**Path**:") -> Optional[str]:
    """
    Extract a file path from an MCP response.

    Looks for patterns like:
    - **Path**: `/path/to/file.js`
    - Path: `/path/to/file.js`

    Args:
        response: The tool response text
        marker: The marker before the path (default: "**Path**:")

    Returns:
        File path or None if not found
    """
    # Try markdown bold format: **Path**: `...`
    pattern = rf"{re.escape(marker)}\s*`([^`]+)`"
    match = re.search(pattern, response)
    if match:
        return match.group(1)

    # Try plain format: Path: /...
    plain_pattern = r"Path:\s*([^\s\n]+)"
    match = re.search(plain_pattern, response)
    if match:
        return match.group(1)

    return None


def extract_nugget_id(response: str) -> Optional[str]:
    """
    Extract the nugget ID from a create_nugget response.

    Looks for patterns like:
    - | **Nugget ID** | `nugget-12345` |
    - Nugget ID: nugget-12345

    Returns:
        Nugget ID or None if not found
    """
    # Table format: | **Nugget ID** | `...` |
    pattern = r"\*\*Nugget ID\*\*\s*\|\s*`([^`]+)`"
    match = re.search(pattern, response)
    if match:
        return match.group(1)

    # Plain format
    pattern = r"Nugget ID:\s*`?([a-zA-Z0-9-]+)`?"
    match = re.search(pattern, response)
    if match:
        return match.group(1)

    return None


def extract_function_id(response: str) -> Optional[str]:
    """
    Extract the function ID from a response.

    Returns:
        Function ID or None if not found
    """
    # Table format
    pattern = r"\*\*Function ID\*\*\s*\|\s*`([^`]+)`"
    match = re.search(pattern, response)
    if match:
        return match.group(1)

    # Plain format
    pattern = r"Function ID:\s*`?([a-zA-Z0-9-]+)`?"
    match = re.search(pattern, response)
    if match:
        return match.group(1)

    return None


def extract_discovered_functions(response: str) -> list[str]:
    """
    Extract the discovered functions list from a search_ez_functions response.

    Looks for the JSON array in the "Next Step" section.

    Returns:
        List of function names
    """
    # Look for: discovered_functions: ["ezMail", "ezLog", ...]
    pattern = r'discovered_functions:\s*(\[.*?\])'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        try:
            import json
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Fallback: look for ez* function names
    pattern = r'\b(ez[A-Z][a-zA-Z]+)\b'
    return list(set(re.findall(pattern, response)))


def is_success_response(response: str) -> bool:
    """
    Check if the response indicates success.

    Returns:
        True if success, False if error
    """
    success_markers = ["✅", "CREATED", "PASSED", "SUCCESS"]
    error_markers = ["❌", "FAILED", "ERROR", "BLOCKED"]

    has_success = any(marker in response for marker in success_markers)
    has_error = any(marker in response for marker in error_markers)

    return has_success and not has_error


def is_error_response(response: str) -> bool:
    """
    Check if the response indicates an error.

    Returns:
        True if error, False otherwise
    """
    error_markers = ["❌", "FAILED", "ERROR", "BLOCKED", "VALIDATION FAILED"]
    return any(marker in response for marker in error_markers)


def extract_error_type(response: str) -> Optional[str]:
    """
    Extract the type of error from a response.

    Returns:
        Error type string or None
    """
    error_patterns = [
        (r"WORKFLOW ERROR", "workflow_error"),
        (r"VALIDATION FAILED", "validation_failed"),
        (r"RUNTIME VALIDATION FAILED", "runtime_validation_failed"),
        (r"STATIC VALIDATION FAILED", "static_validation_failed"),
        (r"API ERROR", "api_error"),
        (r"NOT FOUND", "not_found"),
        (r"UNAUTHORIZED", "unauthorized"),
    ]

    for pattern, error_type in error_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            return error_type

    return None


def extract_table_value(response: str, key: str) -> Optional[str]:
    """
    Extract a value from a markdown table.

    Looks for: | **Key** | `value` |

    Args:
        response: The tool response
        key: The table key (e.g., "Nugget ID", "Label")

    Returns:
        The value or None
    """
    pattern = rf"\*\*{re.escape(key)}\*\*\s*\|\s*`?([^`|\n]+)`?"
    match = re.search(pattern, response)
    return match.group(1).strip() if match else None
