#!/usr/bin/env python3
"""Simple test runner to check pytest functionality."""

import subprocess
import sys


def run_tests():
    """Run a simple test to verify pytest is working."""
    try:
        # Try running a single test file
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit/test_config.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("Test run timed out")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
