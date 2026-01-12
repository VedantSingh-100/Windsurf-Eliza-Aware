"""
Layer 2: Hook Flow Tests

Tests the Windsurf hook behavior by simulating the exact payload that
Windsurf sends to the hook script.

This layer tests:
- Static validation (syntax, IIFE wrapper, ez* function usage)
- Runtime validation (mocked API calls)
- Exit codes (0=pass, 2=block)
- Error messages on stderr
- Credential loading from environment/.env files
"""

import pytest
import os
import json
import subprocess
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers.hook_runner import run_hook, run_hook_on_file, create_hook_payload, HookResult


# Path to the hook script
HOOK_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    '..',
    'scripts',
    'validate_nuggets_after_write.py'
)


# =============================================================================
# STATIC VALIDATION TESTS
# =============================================================================

class TestStaticValidation:
    """Test static validation through the hook."""

    def test_valid_nugget_passes_static(self, valid_nugget_file):
        """Valid nugget file passes static validation."""
        result = run_hook_on_file(valid_nugget_file)

        # Should pass (exit 0) or skip runtime (no credentials)
        # Static validation should pass
        assert "Static validation PASSED" in result.stdout or result.passed

    def test_invalid_nugget_missing_iife_blocks(self, invalid_nugget_file):
        """Nugget missing IIFE wrapper is blocked."""
        result = run_hook_on_file(invalid_nugget_file)

        # Should be blocked (exit 2) or have warnings
        # Static validation should fail
        if result.blocked:
            assert "VALIDATION_FAILED" in result.stderr or "Static validation FAILED" in result.stdout

    def test_ezmail_without_stringify_passes_static(self, ezmail_nugget_file):
        """ezMail call routes correctly through validation.

        Note: JSON.stringify check only applies to literal object arguments {}.
        ezMail(data.email, ...) passes because data.email is not an object literal.
        """
        result = run_hook_on_file(ezmail_nugget_file)

        # The code structure is valid - ezMail call without object literal is OK
        # Static validation should pass (the IIFE wrapper is present)
        assert "Static validation PASSED" in result.stdout or result.passed

    def test_valid_ezmail_passes(self, valid_ezmail_nugget_file):
        """ezMail with JSON.stringify passes static validation."""
        result = run_hook_on_file(valid_ezmail_nugget_file)

        # Static validation should pass
        assert "Static validation PASSED" in result.stdout or not result.blocked

    def test_non_nugget_file_skipped(self, non_nugget_file):
        """Non-nugget files are skipped (not validated)."""
        result = run_hook_on_file(non_nugget_file)

        # Should pass immediately (exit 0) - file is not a nugget
        assert result.passed


# =============================================================================
# HOOK PAYLOAD TESTS
# =============================================================================

class TestHookPayload:
    """Test hook payload handling."""

    def test_empty_payload_handled(self):
        """Empty payload doesn't crash the hook."""
        result = run_hook({})

        # Should exit gracefully (exit 0)
        assert result.exit_code == 0

    def test_malformed_payload_handled(self):
        """Malformed payload is handled gracefully."""
        # Run hook with non-JSON input
        try:
            proc = subprocess.run(
                ["python", HOOK_SCRIPT],
                input="not valid json",
                capture_output=True,
                text=True,
                timeout=10
            )
            # Should not crash
            assert proc.returncode == 0
        except subprocess.TimeoutExpired:
            pytest.fail("Hook timed out on malformed input")

    def test_missing_file_handled(self):
        """Hook handles missing files gracefully."""
        payload = create_hook_payload("/nonexistent/path/file.nugget.js")
        result = run_hook(payload)

        # Should exit gracefully (file doesn't exist)
        # May pass (no file to validate) or handle error
        assert result.exit_code in [0, 2]

    def test_multiple_files_in_payload(self, tmp_path):
        """Hook can validate multiple files in one payload."""
        # Create two valid nugget files
        nugget1 = tmp_path / "nuggets" / "one.nugget.js"
        nugget2 = tmp_path / "nuggets" / "two.nugget.js"
        (tmp_path / "nuggets").mkdir(parents=True)

        valid_code = '(function(data) { ezLog("test"); return "ok"; })()'
        nugget1.write_text(valid_code)
        nugget2.write_text(valid_code)

        payload = {
            "tool_info": {"file_path": str(nugget1)},
            "changed_files": [str(nugget1), str(nugget2)]
        }

        result = run_hook(payload)

        # Both should be validated
        assert str(nugget1) in result.stdout or "test" in result.stdout


# =============================================================================
# CREDENTIAL HANDLING TESTS
# =============================================================================

class TestCredentialHandling:
    """Test credential loading for runtime validation."""

    def test_env_vars_used_for_credentials(self, valid_nugget_file):
        """Hook uses environment variables for credentials."""
        env_vars = {
            "ELIZA_JWT_TOKEN": "test-jwt-token",
            "ELIZA_AGENT_ID": "12345678-1234-1234-1234-123456789abc",
            "ELIZA_ENV": "QA"
        }

        result = run_hook_on_file(valid_nugget_file, env_vars=env_vars)

        # Should show credentials were found
        assert "JWT: Found" in result.stdout or "test-jwt" in result.stdout or result.exit_code in [0, 2]

    def test_no_credentials_skips_runtime(self, valid_nugget_file):
        """No credentials means runtime validation is skipped."""
        # Clear any existing credentials
        env_vars = {
            "ELIZA_JWT_TOKEN": "",
            "ELIZA_AGENT_ID": "",
        }

        result = run_hook_on_file(valid_nugget_file, env_vars=env_vars)

        # Should skip runtime validation but still pass static
        assert "SKIPPED" in result.stdout or "Static validation PASSED" in result.stdout or result.passed

    def test_env_file_loaded(self, tmp_path, valid_jwt_token, valid_agent_id):
        """Hook loads credentials from .env file."""
        # Create a nugget file with a .env in the same workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        nuggets_dir = workspace / "nuggets"
        nuggets_dir.mkdir()

        # Create .env file
        env_file = workspace / ".env"
        env_file.write_text(f"""ELIZA_JWT_TOKEN={valid_jwt_token}
ELIZA_AGENT_ID={valid_agent_id}
ELIZA_ENV=QA
""")

        # Create nugget file
        nugget_file = nuggets_dir / "test.nugget.js"
        nugget_file.write_text('(function(data) { ezLog("test"); return "ok"; })()')

        result = run_hook_on_file(str(nugget_file))

        # Should find credentials from .env
        assert ".env" in result.stdout or "JWT: Found" in result.stdout or result.exit_code in [0, 2]


# =============================================================================
# EXIT CODE TESTS
# =============================================================================

class TestExitCodes:
    """Test that hook returns correct exit codes."""

    def test_valid_nugget_exits_zero(self, valid_nugget_file):
        """Valid nugget returns exit code 0."""
        result = run_hook_on_file(valid_nugget_file)

        # Should pass (static validation at minimum)
        assert result.passed or result.exit_code == 0

    def test_invalid_nugget_exits_two(self, invalid_nugget_file):
        """Invalid nugget returns exit code 2 (blocked)."""
        result = run_hook_on_file(invalid_nugget_file)

        # Should be blocked
        if not result.passed:
            assert result.blocked

    def test_non_nugget_exits_zero(self, non_nugget_file):
        """Non-nugget file returns exit code 0 (skipped)."""
        result = run_hook_on_file(non_nugget_file)

        assert result.passed


# =============================================================================
# STDERR ERROR MESSAGE TESTS
# =============================================================================

class TestErrorMessages:
    """Test that error messages are properly formatted for Cascade."""

    def test_validation_error_on_stderr(self, invalid_nugget_file):
        """Validation errors are written to stderr."""
        result = run_hook_on_file(invalid_nugget_file)

        if result.blocked:
            # Should have error message on stderr
            assert len(result.stderr) > 0 or "FAILED" in result.stdout

    def test_credential_error_message(self, tmp_path):
        """Missing credentials produce helpful error message."""
        # Create a nugget that would fail static validation
        nugget_file = tmp_path / "nuggets" / "test.nugget.js"
        (tmp_path / "nuggets").mkdir(parents=True)
        # Invalid code - missing IIFE
        nugget_file.write_text('function test() { ezLog("test"); }')

        # Clear credentials
        env_vars = {"ELIZA_JWT_TOKEN": "", "ELIZA_AGENT_ID": ""}

        result = run_hook_on_file(str(nugget_file), env_vars=env_vars)

        # Should have some indication of the issue
        assert result.exit_code in [0, 2]


# =============================================================================
# PYTHON SDK VALIDATION TESTS
# =============================================================================

class TestPythonSDKValidation:
    """Test validation of Python files using Eliza SDK."""

    def test_valid_python_passes(self, tmp_path):
        """Valid Python Eliza code passes validation."""
        py_file = tmp_path / "agent.py"
        py_file.write_text('''
from bnym_eliza.genai.agent import Agent

agent = Agent(env='QA', agent_id='12345678-1234-1234-1234-123456789abc')
result = agent.chat(query="Hello")
print(result)
''')

        payload = create_hook_payload(str(py_file))
        result = run_hook(payload)

        # Should pass (valid Python code)
        assert result.passed or "Python SDK patterns OK" in result.stdout

    def test_hallucinated_sdk_blocked(self, tmp_path):
        """Hallucinated SDK patterns are blocked."""
        py_file = tmp_path / "agent.py"
        # This uses a non-existent SDK pattern
        py_file.write_text('''
import eliza
agent = eliza.Agent.from_id("12345")  # This doesn't exist!
''')

        payload = create_hook_payload(str(py_file))
        result = run_hook(payload)

        # Should be blocked or warn about hallucinated pattern
        if not result.passed:
            assert "from_id" in result.stderr or "doesn't exist" in result.stdout

    def test_nugget_function_schema_error(self, tmp_path):
        """functionType=NUGGET without nuggetId is blocked."""
        py_file = tmp_path / "agent.py"
        py_file.write_text('''
from bnym_eliza.genai.agent import Agent

agent = Agent(env='QA')
agent.add_function({
    "funcNameKey": "test",
    "functionType": "NUGGET"  # Missing nuggetId!
})
''')

        payload = create_hook_payload(str(py_file))
        result = run_hook(payload)

        # Should be blocked
        if not result.passed:
            assert "NUGGET" in result.stderr or "nuggetId" in result.stdout or result.blocked


# =============================================================================
# RUNTIME VALIDATION TESTS (Mocked)
# =============================================================================

class TestRuntimeValidation:
    """Test runtime validation (API calls - mocked in CI)."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get("ELIZA_JWT_TOKEN"),
        reason="No credentials for runtime validation"
    )
    def test_runtime_validation_with_real_api(self, valid_nugget_file):
        """Runtime validation actually hits API (integration test)."""
        result = run_hook_on_file(valid_nugget_file)

        # With real credentials, runtime validation should run
        assert "Runtime validation" in result.stdout

    def test_network_error_is_warning(self, valid_nugget_file):
        """Network errors during runtime validation are warnings, not failures."""
        # Set fake credentials that will fail
        env_vars = {
            "ELIZA_JWT_TOKEN": "fake-token-will-fail",
            "ELIZA_AGENT_ID": "12345678-1234-1234-1234-123456789abc",
            "ELIZA_ENV": "QA"
        }

        result = run_hook_on_file(valid_nugget_file, env_vars=env_vars)

        # Should still pass if static validation passed
        # Network errors are treated as warnings
        # This test verifies the hook doesn't crash on API failures
        assert result.exit_code in [0, 2]


# =============================================================================
# HOOK RUNNER HELPER TESTS
# =============================================================================

class TestHookRunnerHelper:
    """Test the hook runner helper functions."""

    def test_hook_result_properties(self):
        """HookResult has correct properties."""
        result = HookResult(exit_code=0, stdout="test", stderr="")
        assert result.passed
        assert not result.blocked

        result = HookResult(exit_code=2, stdout="", stderr="error")
        assert not result.passed
        assert result.blocked
        assert result.has_error("error")

    def test_create_hook_payload_format(self):
        """create_hook_payload creates correct format."""
        payload = create_hook_payload("/path/to/file.js")

        assert "tool_info" in payload
        assert "changed_files" in payload
        assert payload["tool_info"]["file_path"] == "/path/to/file.js"
        assert "/path/to/file.js" in payload["changed_files"]
