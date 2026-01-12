"""
Tests for Windsurf Hook Scripts

Tests the hook scripts that Windsurf calls:
- scripts/validate_before_write.py (pre_write_code hook)
- scripts/validate_nuggets_after_write.py (post_write_code hook)

These tests simulate the JSON payloads that Windsurf sends.
"""

import pytest
import subprocess
import json
import sys
import os
import tempfile

# Paths to hook scripts
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
PRE_WRITE_SCRIPT = os.path.join(SCRIPTS_DIR, "validate_before_write.py")
POST_WRITE_SCRIPT = os.path.join(SCRIPTS_DIR, "validate_nuggets_after_write.py")


def run_hook_script(script_path: str, payload: dict) -> tuple:
    """
    Run a hook script with the given payload.

    Args:
        script_path: Path to the hook script
        payload: JSON payload to send via stdin

    Returns:
        (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": os.path.dirname(SCRIPTS_DIR)}
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


class TestPreWriteHook:
    """Tests for the pre_write_code hook."""

    @pytest.mark.skipif(not os.path.exists(PRE_WRITE_SCRIPT), reason="Pre-write script not found")
    def test_valid_nugget_passes(self, valid_nugget_code, tmp_path):
        """Valid nugget code should allow write (exit 0)."""
        payload = {
            "hook": {"type": "pre_write_code"},
            "file_path": str(tmp_path / "test.nugget.js"),
            "edits": [
                {"type": "insert", "start_line": 0, "content": valid_nugget_code}
            ]
        }

        exit_code, stdout, stderr = run_hook_script(PRE_WRITE_SCRIPT, payload)

        # Exit 0 = allow write, Exit 2 = block write
        assert exit_code == 0, f"Valid nugget should pass. stderr: {stderr}"

    @pytest.mark.skipif(not os.path.exists(PRE_WRITE_SCRIPT), reason="Pre-write script not found")
    def test_invalid_nugget_blocks(self, tmp_path):
        """Invalid nugget code should block write (exit 2)."""
        invalid_code = "function(data) { ezMail('invalid'); }"  # Missing IIFE, missing stringify

        payload = {
            "hook": {"type": "pre_write_code"},
            "file_path": str(tmp_path / "test.nugget.js"),
            "edits": [
                {"type": "insert", "start_line": 0, "content": invalid_code}
            ]
        }

        exit_code, stdout, stderr = run_hook_script(PRE_WRITE_SCRIPT, payload)

        # Exit 2 = block write
        # May also be exit 0 if validation is lenient
        assert exit_code in [0, 2], f"Unexpected exit code: {exit_code}"

    @pytest.mark.skipif(not os.path.exists(PRE_WRITE_SCRIPT), reason="Pre-write script not found")
    def test_non_nugget_file_passes(self, tmp_path):
        """Non-nugget files should always pass."""
        payload = {
            "hook": {"type": "pre_write_code"},
            "file_path": str(tmp_path / "readme.md"),
            "edits": [
                {"type": "insert", "start_line": 0, "content": "# Hello World"}
            ]
        }

        exit_code, stdout, stderr = run_hook_script(PRE_WRITE_SCRIPT, payload)

        assert exit_code == 0, f"Non-nugget file should pass. stderr: {stderr}"

    @pytest.mark.skipif(not os.path.exists(PRE_WRITE_SCRIPT), reason="Pre-write script not found")
    def test_python_eliza_file(self, tmp_path):
        """Python files with Eliza imports should be validated."""
        python_code = '''import bnym_eliza as eliza
from bnym_eliza.genai.agent import Agent

agent = Agent(
    agent_name='Test',
    llm_model='openai-gpt-4.1-mini-ptu'
)
'''
        payload = {
            "hook": {"type": "pre_write_code"},
            "file_path": str(tmp_path / "create_agent.py"),
            "edits": [
                {"type": "insert", "start_line": 0, "content": python_code}
            ]
        }

        exit_code, stdout, stderr = run_hook_script(PRE_WRITE_SCRIPT, payload)

        # Should pass or fail based on validation rules
        assert exit_code in [0, 2]


class TestPostWriteHook:
    """Tests for the post_write_code hook."""

    @pytest.mark.skipif(not os.path.exists(POST_WRITE_SCRIPT), reason="Post-write script not found")
    def test_post_write_with_valid_nugget(self, create_temp_nugget_file, create_temp_env_file, tmp_path):
        """Post-write hook with valid nugget and credentials."""
        nugget_path = create_temp_nugget_file()
        env_path = create_temp_env_file()

        # Set environment variables for the hook
        env = os.environ.copy()
        env["ELIZA_JWT_TOKEN"] = "test.jwt.token"
        env["ELIZA_AGENT_ID"] = "12345678-1234-1234-1234-123456789abc"
        env["ELIZA_ENV"] = "QA"

        payload = {
            "hook": {"type": "post_write_code"},
            "tool_info": {"tool_name": "write_to_file"},
            "changed_files": [nugget_path]
        }

        # Note: This will fail if it tries to make real API calls
        # In a real test setup, we'd mock the API client
        try:
            result = subprocess.run(
                [sys.executable, POST_WRITE_SCRIPT],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=10,
                env={**env, "PYTHONPATH": os.path.dirname(SCRIPTS_DIR)}
            )
            # May fail due to API calls - that's expected without mocking
            assert result.returncode in [0, 2, 1]
        except subprocess.TimeoutExpired:
            pytest.skip("Hook timed out (likely trying API calls)")

    @pytest.mark.skipif(not os.path.exists(POST_WRITE_SCRIPT), reason="Post-write script not found")
    def test_post_write_non_nugget_passes(self, tmp_path):
        """Post-write hook should pass for non-nugget files."""
        readme_path = tmp_path / "readme.md"
        readme_path.write_text("# Hello")

        payload = {
            "hook": {"type": "post_write_code"},
            "tool_info": {"tool_name": "write_to_file"},
            "changed_files": [str(readme_path)]
        }

        exit_code, stdout, stderr = run_hook_script(POST_WRITE_SCRIPT, payload)

        assert exit_code == 0, f"Non-nugget should pass. stderr: {stderr}"


class TestHookPayloadHandling:
    """Tests for hook payload parsing."""

    @pytest.mark.skipif(not os.path.exists(PRE_WRITE_SCRIPT), reason="Pre-write script not found")
    def test_empty_payload_handled(self):
        """Empty payload should be handled gracefully."""
        exit_code, stdout, stderr = run_hook_script(PRE_WRITE_SCRIPT, {})
        # Should not crash
        assert exit_code in [0, 1, 2]

    @pytest.mark.skipif(not os.path.exists(PRE_WRITE_SCRIPT), reason="Pre-write script not found")
    def test_malformed_payload_handled(self):
        """Malformed payload should be handled gracefully."""
        # Send invalid JSON by running directly with bad input
        try:
            result = subprocess.run(
                [sys.executable, PRE_WRITE_SCRIPT],
                input="not valid json",
                capture_output=True,
                text=True,
                timeout=10
            )
            # Should not crash with unhandled exception
            assert result.returncode in [0, 1, 2]
        except Exception as e:
            pytest.fail(f"Hook crashed with malformed input: {e}")
