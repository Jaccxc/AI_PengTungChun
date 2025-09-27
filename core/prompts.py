"""
Prompt templates for the three-stage Claude debugging pipeline.
"""


def step1_prompt(project_root: str, description: str) -> str:
    """
    Generate Step 1 prompt for scoping and analysis.

    Args:
        project_root: Path to the project root
        description: User's task description

    Returns:
        Formatted prompt for Step 1
    """
    return f"""[SYSTEM]
You are an expert codebase investigator. First understand the repository
structure and how the described issue might manifest. Be concise; produce a focused
report and a proposed search plan. Do NOT modify any files in this step.

Task: Understand the scope and narrow the search.
Project root: {project_root}
User description:
{description}

Output:
1) Likely impacted modules/packages
2) How components interact with the bug/feature
3) Shortlist of files/functions to inspect next
"""


def step2_prompt(step1_path: str, tests_dir: str) -> str:
    """
    Generate Step 2 prompt for writing failing tests.

    Args:
        step1_path: Path to step1.md analysis file
        tests_dir: Directory where tests should be written

    Returns:
        Formatted prompt for Step 2
    """
    return f"""[SYSTEM]
You are a senior test engineer. Generate minimal failing tests that capture the intended
behavior. Use pytest. Keep tests deterministic and small.

Using the analysis from: {step1_path}
Write tests ONLY under: {tests_dir}
- Use pytest; name files like test_bugfix_*.py.
- Keep each file short and focused.
- If project APIs are unclear, create minimal fakes/mocks.

At the VERY END, print exactly one line:
RESULT: TESTS_WRITTEN"""


def step3_prompt(tests_dir: str, step1_report_path: str, step2_report_path: str, attempt: int, max_attempts: int) -> str:
    """
    Generate Step 3 prompt for fixing and running tests.

    Args:
        tests_dir: Directory containing tests to run
        attempt: Current attempt number
        max_attempts: Maximum number of attempts allowed

    Returns:
        Formatted prompt for Step 3
    """
    return f"""[SYSTEM]
                You are a surgical code fixer. Iterate: run tests, propose smallest change set, apply, re-run,
                until green or max attempts reached. Avoid irrelevant edits.

                see {step1_report_path} for the analysis.
                see {step2_report_path} for the info about tests made.

                Goal: Make tests in {tests_dir} pass.
                You MUST execute all commands yourself.

                Run tests with:
                python -m pytest "{tests_dir}" -q

                If failing:
                - Apply the smallest possible code changes
                - Re-run tests
                - Repeat until green or attempts exhausted

                At the ABSOLUTE END of your output, print exactly ONE line:
                RESULT: PASS
                or
                RESULT: FAIL

                Attempt {attempt} of {max_attempts}."""