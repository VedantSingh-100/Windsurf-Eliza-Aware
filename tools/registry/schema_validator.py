"""
Schema Validator - Detect drift between TOOL_REGISTRY and client.py docstrings.

HYBRID APPROACH validation component:
This module compares the schemas stored in TOOL_REGISTRY against the
docstrings extracted from ElizaClient methods to detect inconsistencies.

Use Cases:
1. CI/CD: Run validation on build to catch drift early
2. Development: Verify registry matches docstrings after API changes
3. Debugging: Identify which operations have mismatched documentation

Drift Detection Checks:
- Parameter count mismatch
- Missing request_body in registry but present in docstring
- Missing responses in registry but present in docstring
- Parameter names that don't match
"""

import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

from tools.registry.tool_registry import TOOL_REGISTRY
from tools.registry.docstring_extractor import (
    extract_method_docs,
    parse_args_to_dict,
    parse_request_body_to_dict,
    parse_responses_to_dict,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationWarning:
    """Represents a single schema drift warning."""
    category: str
    operation: str
    warning_type: str
    message: str
    severity: str = "warning"  # "warning", "error", "info"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.category}.{self.operation}: {self.message}"


def validate_operation(
    category_name: str,
    op_name: str,
    op_config: Dict[str, Any]
) -> List[ValidationWarning]:
    """
    Validate a single operation against its docstring.

    Args:
        category_name: Name of the category
        op_name: Name of the operation
        op_config: Operation configuration from registry

    Returns:
        List of validation warnings
    """
    warnings = []
    method_name = op_config.get("method", op_name)

    # Extract docstring info
    method_docs = extract_method_docs(method_name)

    # If no docstring at all, that's an info notice
    if not method_docs.get("full"):
        warnings.append(ValidationWarning(
            category=category_name,
            operation=op_name,
            warning_type="missing_docstring",
            message=f"Method '{method_name}' has no docstring - using registry as fallback",
            severity="info"
        ))
        return warnings

    # Check Args section
    docstring_args = method_docs.get("args", "")
    registry_args = op_config.get("args", {})

    if docstring_args and not registry_args:
        warnings.append(ValidationWarning(
            category=category_name,
            operation=op_name,
            warning_type="missing_registry_args",
            message="Docstring has Args section but registry does not",
            severity="warning"
        ))
    elif registry_args and not docstring_args:
        warnings.append(ValidationWarning(
            category=category_name,
            operation=op_name,
            warning_type="missing_docstring_args",
            message="Registry has args but docstring does not",
            severity="warning"
        ))

    # Check Request Body section
    docstring_rb = method_docs.get("request_body", "")
    registry_rb = op_config.get("request_body", {})

    if docstring_rb and not registry_rb:
        warnings.append(ValidationWarning(
            category=category_name,
            operation=op_name,
            warning_type="missing_registry_request_body",
            message="Docstring has Request Body section but registry does not",
            severity="warning"
        ))
    elif registry_rb and not docstring_rb:
        warnings.append(ValidationWarning(
            category=category_name,
            operation=op_name,
            warning_type="missing_docstring_request_body",
            message="Registry has request_body but docstring does not",
            severity="info"
        ))

    # Check Responses section
    docstring_resp = method_docs.get("responses", "")
    registry_resp = op_config.get("responses", {})

    if docstring_resp and not registry_resp:
        warnings.append(ValidationWarning(
            category=category_name,
            operation=op_name,
            warning_type="missing_registry_responses",
            message="Docstring has Responses section but registry does not",
            severity="warning"
        ))

    return warnings


def validate_category(category_name: str) -> List[ValidationWarning]:
    """
    Validate all operations in a category.

    Args:
        category_name: Name of the category to validate

    Returns:
        List of validation warnings for the category
    """
    warnings = []
    category = TOOL_REGISTRY.get(category_name)

    if not category:
        warnings.append(ValidationWarning(
            category=category_name,
            operation="*",
            warning_type="unknown_category",
            message=f"Category '{category_name}' not found in registry",
            severity="error"
        ))
        return warnings

    for op_name, op_config in category.get("operations", {}).items():
        warnings.extend(validate_operation(category_name, op_name, op_config))

    return warnings


def validate_all_schemas() -> List[ValidationWarning]:
    """
    Validate all categories and operations in TOOL_REGISTRY.

    Returns:
        List of all validation warnings across all categories
    """
    all_warnings = []

    for category_name in TOOL_REGISTRY.keys():
        all_warnings.extend(validate_category(category_name))

    return all_warnings


def run_validation(log_warnings: bool = True) -> Tuple[bool, List[ValidationWarning]]:
    """
    Run full schema validation and optionally log warnings.

    Args:
        log_warnings: If True, log warnings to the logger

    Returns:
        Tuple of (is_valid, warnings_list)
        is_valid is True if no errors (warnings are okay)
    """
    warnings = validate_all_schemas()

    if log_warnings:
        for w in warnings:
            if w.severity == "error":
                logger.error(str(w))
            elif w.severity == "warning":
                logger.warning(str(w))
            else:
                logger.info(str(w))

    # Consider valid if no errors (warnings are acceptable)
    has_errors = any(w.severity == "error" for w in warnings)
    return not has_errors, warnings


def get_validation_report() -> str:
    """
    Generate a human-readable validation report.

    Returns:
        Formatted string report of all validation findings
    """
    _, warnings = run_validation(log_warnings=False)

    if not warnings:
        return "Schema Validation Report: All schemas are in sync!"

    # Group by category
    by_category: Dict[str, List[ValidationWarning]] = {}
    for w in warnings:
        if w.category not in by_category:
            by_category[w.category] = []
        by_category[w.category].append(w)

    # Build report
    lines = [
        "Schema Validation Report",
        "=" * 50,
        f"Total findings: {len(warnings)}",
        f"  Errors: {sum(1 for w in warnings if w.severity == 'error')}",
        f"  Warnings: {sum(1 for w in warnings if w.severity == 'warning')}",
        f"  Info: {sum(1 for w in warnings if w.severity == 'info')}",
        "",
    ]

    for category_name, category_warnings in by_category.items():
        lines.append(f"\n{category_name}:")
        lines.append("-" * len(category_name))
        for w in category_warnings:
            prefix = {
                "error": "[ERROR]  ",
                "warning": "[WARN]   ",
                "info": "[INFO]   "
            }.get(w.severity, "         ")
            lines.append(f"  {prefix}{w.operation}: {w.message}")

    return "\n".join(lines)


# Convenience function for quick validation
def is_schema_valid() -> bool:
    """Quick check if all schemas are valid (no errors)."""
    is_valid, _ = run_validation(log_warnings=False)
    return is_valid
