"""
Docstring Extractor - Extract rich documentation from ElizaClient methods.

This module parses docstrings from api/client.py methods and extracts:
- Full docstring text
- Args section with parameter descriptions
- Request Body schema with field details
- Response codes with meanings

Used by category_router.py to build rich MCP Tool descriptions.
"""

import inspect
import re
from typing import Dict, Optional, Any
from api.client import ElizaClient


def extract_method_docs(method_name: str) -> Dict[str, str]:
    """
    Extract structured documentation from an ElizaClient method.

    Args:
        method_name: Name of the method on ElizaClient (e.g., 'chat', 'create_agent')

    Returns:
        Dict with keys:
        - full: Complete docstring text
        - args: Args section content
        - request_body: Request Body section content
        - responses: Responses section content
    """
    method = getattr(ElizaClient, method_name, None)
    if not method:
        return {"full": "", "args": "", "request_body": "", "responses": ""}

    docstring = inspect.getdoc(method) or ""

    return {
        "full": docstring,
        "args": extract_args_section(docstring),
        "request_body": extract_request_body_section(docstring),
        "responses": extract_responses_section(docstring),
    }


def extract_args_section(docstring: str) -> str:
    """
    Extract the Args section from a docstring.

    Args:
        docstring: Full docstring text

    Returns:
        Args section content (without the 'Args:' header)
    """
    if not docstring:
        return ""

    # Match Args: section until next section or end
    match = re.search(
        r'Args:\s*\n(.*?)(?=\n\s*(?:Request Body|Returns|Responses|Note|$))',
        docstring,
        re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else ""


def extract_request_body_section(docstring: str) -> str:
    """
    Extract the Request Body section from a docstring.

    Args:
        docstring: Full docstring text

    Returns:
        Request Body section content (without the header)
    """
    if not docstring:
        return ""

    # Match "Request Body (SchemaName):" or "Request Body:" section
    match = re.search(
        r'Request Body\s*(?:\([^)]+\))?\s*:\s*\n(.*?)(?=\n\s*(?:Returns|Responses|Note|$))',
        docstring,
        re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else ""


def extract_responses_section(docstring: str) -> str:
    """
    Extract the Responses section from a docstring.

    Args:
        docstring: Full docstring text

    Returns:
        Responses section content (without the 'Responses:' header)
    """
    if not docstring:
        return ""

    # Match Responses: section until end or Note
    match = re.search(
        r'Responses:\s*\n(.*?)(?=\n\s*(?:Note|$)|$)',
        docstring,
        re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else ""


def parse_args_to_dict(args_text: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse Args section text into structured dict.

    Args:
        args_text: Raw text from Args section

    Returns:
        Dict mapping param names to {type, required, description}
    """
    result = {}
    if not args_text:
        return result

    # Match lines like "param_name: type (required/optional) - Description"
    pattern = r'(\w+):\s*(\w+(?:\[[^\]]+\])?)\s*(?:\((\w+)\))?\s*(?:-\s*)?(.+?)(?=\n\s*\w+:|$)'

    for match in re.finditer(pattern, args_text, re.DOTALL):
        param_name = match.group(1)
        param_type = match.group(2)
        required_str = match.group(3) or ""
        description = match.group(4).strip()

        result[param_name] = {
            "type": param_type,
            "required": "required" in required_str.lower(),
            "description": description
        }

    return result


def parse_request_body_to_dict(request_body_text: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse Request Body section text into structured dict.

    Args:
        request_body_text: Raw text from Request Body section

    Returns:
        Dict mapping field names to {type, required, description}
    """
    result = {}
    if not request_body_text:
        return result

    # Match lines like "- fieldName: type - Description" or "- fieldName: type (required) - Description"
    pattern = r'-\s*(\w+):\s*(\w+(?:\[[^\]]+\])?)\s*(?:\(([^)]+)\))?\s*(?:-\s*)?(.+?)(?=\n\s*-|\Z)'

    for match in re.finditer(pattern, request_body_text, re.DOTALL):
        field_name = match.group(1)
        field_type = match.group(2)
        modifier = match.group(3) or ""
        description = match.group(4).strip()

        result[field_name] = {
            "type": field_type,
            "required": "required" in modifier.lower(),
            "description": description
        }

    return result


def parse_responses_to_dict(responses_text: str) -> Dict[str, str]:
    """
    Parse Responses section text into dict of status codes.

    Args:
        responses_text: Raw text from Responses section

    Returns:
        Dict mapping status codes to descriptions
    """
    result = {}
    if not responses_text:
        return result

    # Match lines like "- 200: Description" or "200: Description"
    pattern = r'-?\s*(\d{3}):\s*(.+?)(?=\n|$)'

    for match in re.finditer(pattern, responses_text):
        status_code = match.group(1)
        description = match.group(2).strip()
        result[status_code] = description

    return result


def get_all_method_docs() -> Dict[str, Dict[str, str]]:
    """
    Extract documentation for ALL public methods in ElizaClient.

    Returns:
        Dict mapping method names to their documentation dicts
    """
    result = {}

    for name in dir(ElizaClient):
        # Skip private methods and non-callables
        if name.startswith('_'):
            continue

        method = getattr(ElizaClient, name, None)
        if not callable(method):
            continue

        # Skip the __init__ and helper methods
        if name in ('__init__', '_request', '_handle_error_response', '_request_legacy'):
            continue

        result[name] = extract_method_docs(name)

    return result


def format_docs_for_description(method_docs: Dict[str, str]) -> str:
    """
    Format extracted docs into a rich description string.

    Args:
        method_docs: Dict from extract_method_docs()

    Returns:
        Formatted string suitable for MCP Tool description
    """
    parts = []

    if method_docs.get("args"):
        parts.append(f"Args:\n{method_docs['args']}")

    if method_docs.get("request_body"):
        parts.append(f"Request Body:\n{method_docs['request_body']}")

    if method_docs.get("responses"):
        parts.append(f"Responses:\n{method_docs['responses']}")

    return "\n\n".join(parts)
