"""
Hook Runner

Simulates Windsurf hook execution by running the hook script as a subprocess
with the expected JSON payload via stdin.

This allows testing the complete hook flow:
1. File written to disk
2. Windsurf triggers hook
3. Hook receives payload via stdin
4. Hook runs validation
5. Hook returns exit code (0=pass, 2=block)
"""

import subprocess
import json
import os
from dataclasses import dataclass
from typing import Optional


# Path to the hook script
HOOK_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    '..',
    'scripts',
    'validate_nuggets_after_write.py'
)


@dataclass
class HookResult:
    """Result from running a hook."""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        """True if hook passed (exit 0)."""
        return self.exit_code == 0

    @property
    def blocked(self) -> bool:
        """True if hook blocked (exit 2)."""
        return self.exit_code == 2

    @property
    def errors(self) -> list[str]:
        """Extract error messages from stderr."""
        return [line for line in self.stderr.strip().split('\n') if line]

    def has_error(self, substring: str) -> bool:
        """Check if a specific error is in stderr."""
        return substring in self.stderr


def run_hook(
    payload: dict,
    env_vars: Optional[dict] = None,
    timeout: int = 30
) -> HookResult:
    """
    Run the post_write_code hook with a simulated Windsurf payload.

    This simulates exactly what Windsurf does:
    1. Sends JSON payload via stdin
    2. Receives exit code, stdout, stderr

    Args:
        payload: The hook payload (tool_info, changed_files, etc.)
        env_vars: Optional environment variables (ELIZA_JWT_TOKEN, etc.)
        timeout: Timeout in seconds

    Returns:
        HookResult with exit_code, stdout, stderr
    """
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    try:
        result = subprocess.run(
            ["python", HOOK_SCRIPT_PATH],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout
        )
        return HookResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )
    except subprocess.TimeoutExpired:
        return HookResult(
            exit_code=-1,
            stdout="",
            stderr="Hook timed out"
        )
    except Exception as e:
        return HookResult(
            exit_code=-1,
            stdout="",
            stderr=f"Hook error: {str(e)}"
        )


def create_hook_payload(
    file_path: str,
    changed_files: Optional[list[str]] = None,
    tool_name: str = "write_to_file"
) -> dict:
    """
    Create a standard Windsurf hook payload.

    Args:
        file_path: The primary file being written
        changed_files: List of all changed files (defaults to [file_path])
        tool_name: The tool that triggered the write

    Returns:
        Hook payload dict
    """
    return {
        "hook": {
            "type": "post_write_code"
        },
        "tool_info": {
            "tool_name": tool_name,
            "file_path": file_path
        },
        "changed_files": changed_files or [file_path]
    }


def run_hook_on_file(
    file_path: str,
    env_vars: Optional[dict] = None,
    timeout: int = 30
) -> HookResult:
    """
    Convenience function to run hook on a single file.

    Args:
        file_path: Path to the file to validate
        env_vars: Optional environment variables
        timeout: Timeout in seconds

    Returns:
        HookResult
    """
    payload = create_hook_payload(file_path)
    return run_hook(payload, env_vars, timeout)
