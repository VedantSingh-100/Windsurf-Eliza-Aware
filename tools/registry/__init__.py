"""
Registry module - Central tool definitions, routing, and documentation.

HYBRID APPROACH (Jan 2026):
This module provides comprehensive tool generation with rich documentation:

1. TOOL_REGISTRY: Full schemas as authoritative reference (version-controlled)
2. Docstring extractor: Extracts docs from ElizaClient at runtime (always current)
3. Category router: Builds rich MCP tools with hybrid documentation
4. Schema validator: Detects drift between registry and docstrings

Architecture:
- 19 category tools route to 75 client methods
- Rich descriptions include Args, Request Body, Response codes
- "When to use" hints improve Windsurf discoverability
- Add new endpoints by updating TOOL_REGISTRY + client.py docstrings
"""

from tools.registry.tool_registry import (
    TOOL_REGISTRY,
    PARAM_SCHEMAS,
    get_category_names,
    get_operations_for_category,
    get_operation_config,
    get_when_to_use,
)
from tools.registry.category_router import (
    create_category_tool,
    handle_category_operation,
    get_all_category_tools,
    OPERATION_TOOLS,
    CATEGORY_HANDLERS,
    build_docs_from_registry,
    build_rich_input_schema,
)
from tools.registry.docstring_extractor import (
    extract_method_docs,
    extract_args_section,
    extract_request_body_section,
    extract_responses_section,
    parse_args_to_dict,
    parse_request_body_to_dict,
    parse_responses_to_dict,
    get_all_method_docs,
    format_docs_for_description,
)
from tools.registry.schema_validator import (
    validate_all_schemas,
    validate_category,
    validate_operation,
    run_validation,
    get_validation_report,
    is_schema_valid,
    ValidationWarning,
)

__all__ = [
    # Registry
    "TOOL_REGISTRY",
    "PARAM_SCHEMAS",
    "get_category_names",
    "get_operations_for_category",
    "get_operation_config",
    "get_when_to_use",
    # Router
    "create_category_tool",
    "handle_category_operation",
    "get_all_category_tools",
    "OPERATION_TOOLS",
    "CATEGORY_HANDLERS",
    "build_docs_from_registry",
    "build_rich_input_schema",
    # Docstring extractor
    "extract_method_docs",
    "extract_args_section",
    "extract_request_body_section",
    "extract_responses_section",
    "parse_args_to_dict",
    "parse_request_body_to_dict",
    "parse_responses_to_dict",
    "get_all_method_docs",
    "format_docs_for_description",
    # Schema validator
    "validate_all_schemas",
    "validate_category",
    "validate_operation",
    "run_validation",
    "get_validation_report",
    "is_schema_valid",
    "ValidationWarning",
]
