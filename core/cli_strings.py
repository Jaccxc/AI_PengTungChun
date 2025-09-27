"""
Canonical sentinel strings and CLI helpers for the Claude Debugger.
"""

# Sentinel strings for each step
STEP2_SENTINEL = "RESULT: TESTS_WRITTEN"
PASS_SENTINEL = "RESULT: PASS"
FAIL_SENTINEL = "RESULT: FAIL"

# CLI command template
CLI_COMMAND_TEMPLATE = "claude --dangerously-skip-permisstions \"{prompt}\""

# Directory names
TEST_DIR_NAME = "test_bugfix"
ARTIFACTS_DIR_NAME = ".claude_tasks"

def check_sentinel_in_output(output: str, sentinel: str) -> bool:
    """
    Check if sentinel appears in the last few lines of output.

    Args:
        output: The command output to check
        sentinel: The sentinel string to look for

    Returns:
        True if sentinel is found in the last 3 lines
    """
    lines = output.strip().splitlines()
    last_lines = lines[-3:] if len(lines) >= 3 else lines

    for line in last_lines:
        if line.strip().upper() == sentinel.upper():
            return True
    return False