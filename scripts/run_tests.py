#!/usr/bin/env python3
"""
Test Runner Script

Runs the test suite with different configurations:
- Unit tests (fast, no API calls)
- Integration tests (requires mock or real API)
- Hook tests (tests hook scripts)
- All tests

Usage:
    python scripts/run_tests.py              # Run all tests
    python scripts/run_tests.py unit         # Run unit tests only
    python scripts/run_tests.py integration  # Run integration tests
    python scripts/run_tests.py hooks        # Run hook tests
    python scripts/run_tests.py coverage     # Run with coverage report
"""

import subprocess
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def run_pytest(args: list = None, markers: str = None):
    """Run pytest with given arguments."""
    cmd = [sys.executable, "-m", "pytest"]

    if markers:
        cmd.extend(["-m", markers])

    if args:
        cmd.extend(args)

    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def run_unit_tests():
    """Run unit tests only (fast, no API calls)."""
    print("\n" + "=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60 + "\n")

    return run_pytest([
        "tests/test_validators.py",
        "tests/test_static_validation.py",
        "tests/test_codegen.py",
    ])


def run_integration_tests():
    """Run integration tests (may require API mocks)."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60 + "\n")

    return run_pytest([
        "tests/test_api_client.py",
    ])


def run_hook_tests():
    """Run hook script tests."""
    print("\n" + "=" * 60)
    print("RUNNING HOOK TESTS")
    print("=" * 60 + "\n")

    return run_pytest([
        "tests/test_hooks.py",
    ])


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RUNNING ALL TESTS")
    print("=" * 60 + "\n")

    return run_pytest()


def run_with_coverage():
    """Run tests with coverage report."""
    print("\n" + "=" * 60)
    print("RUNNING TESTS WITH COVERAGE")
    print("=" * 60 + "\n")

    return run_pytest([
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_report",
        "--cov-exclude=tests/*",
        "--cov-exclude=scripts/*",
    ])


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        mode = "all"
    else:
        mode = sys.argv[1].lower()

    # Check pytest is installed
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed. Run: pip install pytest pytest-cov")
        return 1

    if mode == "unit":
        return run_unit_tests()
    elif mode == "integration":
        return run_integration_tests()
    elif mode == "hooks":
        return run_hook_tests()
    elif mode == "coverage":
        return run_with_coverage()
    elif mode == "all":
        return run_all_tests()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python scripts/run_tests.py [unit|integration|hooks|coverage|all]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
