"""
Unit Tests for Schema Validation and Docstring Extraction

Tests the HYBRID approach implementation:
- tools/registry/docstring_extractor.py - Docstring extraction
- tools/registry/schema_validator.py - Drift detection
- tools/registry/category_router.py - Rich tool generation

Validates that:
1. Docstrings are correctly extracted from ElizaClient
2. Registry schemas are complete and valid
3. Category tools include rich descriptions
4. Schema drift is detected
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
from tools.registry.tool_registry import (
    TOOL_REGISTRY,
    get_category_names,
    get_operations_for_category,
)
from tools.registry.category_router import (
    create_category_tool,
    build_docs_from_registry,
    build_rich_input_schema,
)


class TestDocstringExtractor:
    """Tests for docstring extraction from ElizaClient."""

    def test_extract_method_docs_returns_dict(self):
        """extract_method_docs should return a dict with expected keys."""
        result = extract_method_docs("chat")
        assert isinstance(result, dict)
        assert "full" in result
        assert "args" in result
        assert "request_body" in result
        assert "responses" in result

    def test_extract_method_docs_unknown_method(self):
        """Unknown method should return empty strings."""
        result = extract_method_docs("nonexistent_method_xyz")
        assert result["full"] == ""
        assert result["args"] == ""
        assert result["request_body"] == ""
        assert result["responses"] == ""

    def test_extract_args_section(self):
        """Args section should be extracted from docstring."""
        docstring = """
        Some description.

        Args:
            param1: string (required) - First parameter
            param2: int (optional) - Second parameter

        Returns:
            Something
        """
        result = extract_args_section(docstring)
        assert "param1" in result
        assert "param2" in result

    def test_extract_request_body_section(self):
        """Request Body section should be extracted from docstring."""
        docstring = """
        Some description.

        Request Body (SomeSchema):
            - field1: string - First field
            - field2: int - Second field

        Responses:
            - 200: Success
        """
        result = extract_request_body_section(docstring)
        assert "field1" in result
        assert "field2" in result

    def test_extract_responses_section(self):
        """Responses section should be extracted from docstring."""
        docstring = """
        Some description.

        Responses:
            - 200: Success
            - 400: Bad Request
            - 500: Internal Server Error
        """
        result = extract_responses_section(docstring)
        assert "200" in result
        assert "400" in result
        assert "500" in result

    def test_parse_args_to_dict(self):
        """Args text should be parsed into structured dict."""
        args_text = """
            agent_id: string (required) - The agent ID
            message: string (required) - The message content
            session_id: string (optional) - Session identifier
        """
        result = parse_args_to_dict(args_text)
        # This tests the parsing logic, may need adjustment based on actual docstring format
        assert isinstance(result, dict)

    def test_get_all_method_docs(self):
        """Should return docs for all public methods."""
        result = get_all_method_docs()
        assert isinstance(result, dict)
        # Should have at least some methods
        assert len(result) > 0

    def test_format_docs_for_description(self):
        """Should format docs into description string."""
        docs = {
            "args": "param1: string - Description",
            "request_body": "field1: string - Field desc",
            "responses": "200: Success"
        }
        result = format_docs_for_description(docs)
        assert isinstance(result, str)


class TestSchemaValidator:
    """Tests for schema drift detection."""

    def test_validate_all_schemas_returns_list(self):
        """validate_all_schemas should return a list of warnings."""
        result = validate_all_schemas()
        assert isinstance(result, list)
        # All items should be ValidationWarning
        for item in result:
            assert isinstance(item, ValidationWarning)

    def test_validate_category_valid_category(self):
        """Validating a valid category should not return errors."""
        result = validate_category("chat_operations")
        assert isinstance(result, list)
        # No ERROR severity items for valid category
        errors = [w for w in result if w.severity == "error"]
        assert len(errors) == 0

    def test_validate_category_unknown_category(self):
        """Validating unknown category should return error."""
        result = validate_category("nonexistent_category")
        assert len(result) > 0
        assert result[0].severity == "error"
        assert "unknown_category" in result[0].warning_type

    def test_run_validation_returns_tuple(self):
        """run_validation should return (bool, list) tuple."""
        is_valid, warnings = run_validation(log_warnings=False)
        assert isinstance(is_valid, bool)
        assert isinstance(warnings, list)

    def test_get_validation_report(self):
        """get_validation_report should return formatted string."""
        result = get_validation_report()
        assert isinstance(result, str)
        assert "Schema Validation Report" in result

    def test_is_schema_valid(self):
        """is_schema_valid should return boolean."""
        result = is_schema_valid()
        assert isinstance(result, bool)

    def test_validation_warning_str(self):
        """ValidationWarning should have string representation."""
        warning = ValidationWarning(
            category="test_category",
            operation="test_op",
            warning_type="test_type",
            message="Test message",
            severity="warning"
        )
        result = str(warning)
        assert "test_category" in result
        assert "test_op" in result
        assert "Test message" in result


class TestToolRegistry:
    """Tests for TOOL_REGISTRY completeness."""

    def test_all_categories_have_operations(self):
        """Each category should have at least one operation."""
        for category_name in get_category_names():
            ops = get_operations_for_category(category_name)
            assert len(ops) > 0, f"{category_name} has no operations"

    def test_all_operations_have_required_fields(self):
        """Each operation should have method, params, description."""
        required_fields = ["method", "params", "description"]
        for category_name in get_category_names():
            category = TOOL_REGISTRY[category_name]
            for op_name, op_config in category["operations"].items():
                for field in required_fields:
                    assert field in op_config, \
                        f"{category_name}.{op_name} missing {field}"

    def test_all_categories_have_when_to_use(self):
        """Each category should have when_to_use hints."""
        for category_name in get_category_names():
            category = TOOL_REGISTRY[category_name]
            assert "when_to_use" in category, \
                f"{category_name} missing when_to_use"
            assert len(category["when_to_use"]) > 0, \
                f"{category_name} has empty when_to_use"

    def test_all_operations_have_args_or_empty_params(self):
        """Operations with params should have args descriptions."""
        for category_name in get_category_names():
            category = TOOL_REGISTRY[category_name]
            for op_name, op_config in category["operations"].items():
                params = op_config.get("params", [])
                args = op_config.get("args", {})
                if params:
                    assert "args" in op_config, \
                        f"{category_name}.{op_name} has params but no args"


class TestCategoryRouter:
    """Tests for category tool generation."""

    def test_create_category_tool_returns_tool(self):
        """create_category_tool should return MCP Tool."""
        from mcp.types import Tool
        result = create_category_tool("chat_operations")
        assert isinstance(result, Tool)
        assert result.name == "chat_operations"

    def test_create_category_tool_has_rich_description(self):
        """Generated tool should have rich description."""
        result = create_category_tool("chat_operations")
        description = result.description

        # Should include when_to_use section
        assert "When to Use" in description

        # Should include operations
        assert "Available Operations" in description

        # Should be substantial (not minimal)
        assert len(description) > 500, \
            f"Description too short: {len(description)} chars"

    def test_create_category_tool_has_input_schema(self):
        """Generated tool should have inputSchema with properties."""
        result = create_category_tool("chat_operations")
        schema = result.inputSchema

        assert "type" in schema
        assert "properties" in schema
        assert "operation" in schema["properties"]

    def test_create_category_tool_includes_defs(self):
        """Generated tool schema should include $defs for complex types."""
        result = create_category_tool("chat_operations")
        schema = result.inputSchema

        # chat_operations has request_body schemas, should have $defs
        assert "$defs" in schema, "chat_operations should have $defs"
        assert "ElizaChatRequest" in schema["$defs"]

    def test_build_docs_from_registry(self):
        """build_docs_from_registry should format registry as docs."""
        op_config = {
            "args": {"param1": "string - Description"},
            "request_body": {
                "schema_name": "TestSchema",
                "fields": {"field1": {"type": "string", "description": "Test"}}
            },
            "responses": {"200": "Success"}
        }
        result = build_docs_from_registry(op_config)
        assert "Args:" in result
        assert "Request Body" in result
        assert "Responses:" in result

    def test_build_rich_input_schema(self):
        """build_rich_input_schema should include $defs."""
        category = TOOL_REGISTRY["chat_operations"]
        result = build_rich_input_schema(category)

        assert "type" in result
        assert "properties" in result
        assert "$defs" in result

    def test_all_categories_generate_valid_tools(self):
        """All categories should generate valid MCP tools."""
        from mcp.types import Tool
        for category_name in get_category_names():
            try:
                result = create_category_tool(category_name)
                assert isinstance(result, Tool)
                assert result.name == category_name
            except Exception as e:
                pytest.fail(f"Failed to generate tool for {category_name}: {e}")


class TestRichDescriptionContent:
    """Tests that verify the content of rich descriptions."""

    def test_chat_operations_description_includes_docstring_content(self):
        """chat_operations should include docstring content from client.py."""
        result = create_category_tool("chat_operations")
        description = result.description

        # Should include content from docstrings (Args/Request Body)
        # These should come from either docstring extraction or registry fallback
        assert "agent_id" in description.lower() or "agentid" in description.lower()

    def test_description_not_minimal(self):
        """Descriptions should not be minimal (the original problem)."""
        for category_name in get_category_names():
            result = create_category_tool(category_name)
            description = result.description

            # Original minimal descriptions were ~200 chars
            # Rich descriptions should be 500+ chars
            assert len(description) > 400, \
                f"{category_name} description too short: {len(description)}"

    def test_schema_includes_operation_enum(self):
        """Input schema should include operation enum with all operations."""
        for category_name in get_category_names():
            result = create_category_tool(category_name)
            schema = result.inputSchema

            operation_schema = schema["properties"]["operation"]
            assert "enum" in operation_schema

            # Enum should match registry operations
            expected_ops = get_operations_for_category(category_name)
            assert set(operation_schema["enum"]) == set(expected_ops)
