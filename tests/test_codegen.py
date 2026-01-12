"""
Tests for Code Generation

Tests the codegen/nugget_generator.py module:
- generate_nugget_code()
- Sanitization functions
- Template generation for different function combinations
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codegen.nugget_generator import (
    generate_nugget_code,
    sanitize_string_for_js,
    sanitize_email_for_js,
    sanitize_query_for_js,
)


class TestSanitization:
    """Tests for input sanitization functions."""

    def test_sanitize_string_escapes_quotes(self):
        """Should escape double and single quotes."""
        result = sanitize_string_for_js('He said "hello" and \'goodbye\'')
        assert '\\"' in result
        assert "\\'" in result

    def test_sanitize_string_escapes_backslash(self):
        """Should escape backslashes."""
        result = sanitize_string_for_js('path\\to\\file')
        assert '\\\\' in result

    def test_sanitize_string_escapes_newlines(self):
        """Should escape newlines."""
        result = sanitize_string_for_js("line1\nline2\rline3")
        assert "\\n" in result
        assert "\\r" in result

    def test_sanitize_string_escapes_script_tags(self):
        """Should escape script tags to prevent XSS."""
        result = sanitize_string_for_js("</script>alert('xss')")
        assert "</script>" not in result
        assert "<\\/script>" in result

    def test_sanitize_string_limits_length(self):
        """Should truncate long strings."""
        long_string = "a" * 2000
        result = sanitize_string_for_js(long_string, max_length=100)
        assert len(result) <= 100

    def test_sanitize_string_handles_empty(self):
        """Should handle empty string."""
        result = sanitize_string_for_js("")
        assert result == ""

    def test_sanitize_string_handles_none(self):
        """Should handle None."""
        result = sanitize_string_for_js(None)
        # Should return empty or handle gracefully
        assert result == "" or result is None

    def test_sanitize_email_valid(self):
        """Valid email should pass through."""
        result = sanitize_email_for_js("user@example.com")
        assert result == "user@example.com"

    def test_sanitize_email_invalid_returns_default(self):
        """Invalid email should return default."""
        result = sanitize_email_for_js("not-an-email")
        assert result == "user@example.com"

    def test_sanitize_email_dangerous_chars(self):
        """Email with dangerous chars should return default."""
        dangerous = [
            'user"@example.com',
            "user'@example.com",
            "user<@example.com",
            "user;@example.com",
        ]
        for email in dangerous:
            result = sanitize_email_for_js(email)
            assert result == "user@example.com", f"Email '{email}' should be rejected"

    def test_sanitize_email_empty(self):
        """Empty email should return default."""
        result = sanitize_email_for_js("")
        assert result == "user@example.com"

    def test_sanitize_query_limits_length(self):
        """Query should be limited to 500 chars."""
        long_query = "search " * 200
        result = sanitize_query_for_js(long_query)
        assert len(result) <= 500

    def test_sanitize_query_escapes_special_chars(self):
        """Query should have special chars escaped."""
        result = sanitize_query_for_js('search "term" with \'quotes\'')
        assert '\\"' in result or "'" not in result  # Escaped


class TestCodeGeneration:
    """Tests for nugget code generation."""

    def test_generate_email_nugget(self):
        """Should generate email nugget code."""
        code, label, desc, test_data = generate_nugget_code(
            ["ezMail"],
            "Send email",
            {"email": "test@example.com"}
        )

        assert "ezMail" in code
        assert "(function(data)" in code
        assert "test@example.com" in code

    def test_generate_search_nugget(self):
        """Should generate search nugget code."""
        code, label, desc, test_data = generate_nugget_code(
            ["ezInternetSearch"],
            "Search internet",
            {"query": "test query"}
        )

        assert "ezInternetSearch" in code
        assert "(function(data)" in code

    def test_generate_llm_nugget(self):
        """Should generate LLM nugget code."""
        code, label, desc, test_data = generate_nugget_code(
            ["ezChatCompletions"],
            "Call LLM",
            {}
        )

        assert "ezChatCompletions" in code
        assert "JSON.stringify" in code  # Should use stringify

    def test_generate_search_email_nugget(self):
        """Should generate combined search+email nugget."""
        code, label, desc, test_data = generate_nugget_code(
            ["ezInternetSearch", "ezMail"],
            "Search and email",
            {"email": "test@example.com", "query": "news"}
        )

        assert "ezInternetSearch" in code
        assert "ezMail" in code

    def test_generate_generic_nugget(self):
        """Should generate generic nugget for unknown combinations."""
        code, label, desc, test_data = generate_nugget_code(
            ["ezLog", "ezUser"],
            "Custom nugget",
            {}
        )

        assert "(function(data)" in code
        # Should include the discovered functions
        assert "ezLog" in code or "ezUser" in code

    def test_generated_code_is_valid_iife(self):
        """Generated code should be valid IIFE."""
        code, _, _, _ = generate_nugget_code(
            ["ezMail"],
            "Test",
            {}
        )

        assert code.strip().startswith("(function(data)")
        assert code.strip().endswith("})")

    def test_test_data_returned(self):
        """Should return appropriate test data."""
        _, _, _, test_data = generate_nugget_code(
            ["ezInternetSearch"],
            "Search",
            {"query": "test"}
        )

        assert "query" in test_data

    def test_label_returned(self):
        """Should return appropriate label."""
        _, label, _, _ = generate_nugget_code(
            ["ezMail"],
            "Send notification email",
            {}
        )

        assert label is not None
        assert len(label) > 0

    def test_sanitizes_email_input(self):
        """Should sanitize email in generated code."""
        code, _, _, _ = generate_nugget_code(
            ["ezMail"],
            "Test",
            {"email": 'malicious"@example.com'}
        )

        # Should use sanitized email
        assert 'malicious"@example.com' not in code

    def test_sanitizes_query_input(self):
        """Should sanitize query in generated code."""
        code, _, _, _ = generate_nugget_code(
            ["ezInternetSearch"],
            "Test",
            {"query": 'search</script>alert("xss")'}
        )

        # Should escape dangerous content
        assert "</script>" not in code
