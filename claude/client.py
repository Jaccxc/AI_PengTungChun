"""
Claude CLI client wrapper for the debugger system.
"""
import asyncio
from pathlib import Path
from typing import Tuple

from core.cli_strings import check_sentinel_in_output


class ClaudeCLIError(Exception):
    """Exception raised when Claude CLI execution fails."""
    pass


class ClaudeClient:
    """
    Client for executing Claude CLI commands with the dangerous flag.

    This client always uses the --dangerously-skip-permisstions flag
    and executes commands in the specified working directory.
    """

    def __init__(self, workdir: Path, exe: str = r"C:\Users\wow gaming\AppData\Roaming\npm\claude.cmd"):
        """
        Initialize the Claude client.

        Args:
            workdir: Working directory for command execution
            exe: Claude executable name/path
        """
        self.workdir = Path(workdir)
        self.exe = exe

    async def run(self, prompt_text: str, timeout: int = 1800) -> str:
        """
        Execute a Claude CLI command.

        Args:
            prompt_text: The prompt to send to Claude
            timeout: Timeout in seconds (default 30 minutes)

        Returns:
            The stdout output from Claude

        Raises:
            ClaudeCLIError: If the command fails
        """
        # Use the .cmd shim instead of .ps1
        cmd = [
            r"C:\Users\wow gaming\AppData\Roaming\npm\claude.cmd",
            "--dangerously-skip-permissions",   # make sure this matches the real CLI spelling
            prompt_text
        ]

        print(f"executing claude command: {cmd}")

        try:
            proc = await asyncio.create_subprocess_exec(
                r"C:\Users\wow gaming\AppData\Roaming\npm\claude.cmd",
                "--dangerously-skip-permissions",
                cwd=str(self.workdir),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            out, err = await proc.communicate(input=prompt_text.encode("utf-8"))

            if proc.returncode != 0:
                error_msg = (err or b"").decode(errors="ignore")
                raise ClaudeCLIError(
                    f"Claude CLI failed with exit code {proc.returncode}: {error_msg}"
                )

            return out.decode(errors="ignore")

        except asyncio.TimeoutError:
            raise ClaudeCLIError(f"Claude CLI command timed out after {timeout} seconds")
        except Exception as e:
            raise ClaudeCLIError(f"Failed to execute Claude CLI: {str(e)}")

    async def run_with_sentinel(self, prompt_text: str, sentinel: str, timeout: int = 1800) -> Tuple[str, bool]:
        """
        Execute Claude CLI and check for a sentinel string.

        Args:
            prompt_text: The prompt to send to Claude
            sentinel: The sentinel string to check for
            timeout: Timeout in seconds

        Returns:
            Tuple of (output, sentinel_found)

        Raises:
            ClaudeCLIError: If the command fails
        """
        output = await self.run(prompt_text, timeout)
        sentinel_found = check_sentinel_in_output(output, sentinel)
        return output, sentinel_found