import sys
import pytest

def run_tests():
    """Run all the test cases for the agents using pytest."""
    # Use pytest to discover and run all tests
    # -v for verbose output
    # Return the exit code (0 if all tests pass, non-zero if any test fails)
    return pytest.main(["-v"])

if __name__ == "__main__":
    sys.exit(run_tests())
