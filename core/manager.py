"""
Background task manager for the Claude Debugger system.
"""
import asyncio
import logging
from pathlib import Path
from queue import Queue
from typing import Optional

from claude import ClaudeClient, ClaudeCLIError
from core.models import TaskItem, TaskStatus, UiEvent, StepResult
from core.prompts import step1_prompt, step2_prompt, step3_prompt
from core.cli_strings import STEP2_SENTINEL, PASS_SENTINEL, FAIL_SENTINEL


logger = logging.getLogger(__name__)


class TaskManager:
    """
    Background task manager that processes debugging tasks through the three-stage pipeline.
    """

    def __init__(self, ui_queue: Queue, max_attempts: int = 3):
        """
        Initialize the task manager.

        Args:
            ui_queue: Queue for sending UI events
            max_attempts: Maximum attempts for Step 3 (fixing)
        """
        self.ui_queue = ui_queue
        self.max_attempts = max_attempts
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        """Start the background worker."""
        if not self.running:
            self.running = True
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self):
        """Stop the background worker."""
        self.running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def add_task(self, task: TaskItem):
        """Add a task to the processing queue."""
        await self.task_queue.put(task)
        self._emit_ui_event("enqueued", task.id, f"Task {task.id.hex[:8]} enqueued")

    def _emit_ui_event(self, kind: str, task_id, payload: str):
        """Emit an event to the UI thread."""
        try:
            event = UiEvent(kind=kind, task_id=task_id, payload=payload)
            self.ui_queue.put(event)
        except Exception as e:
            logger.error(f"Failed to emit UI event: {e}")

    async def _worker_loop(self):
        """Main worker loop that processes tasks."""
        while self.running:
            try:
                # Wait for a task with timeout to allow checking running flag
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                await self._process_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

    async def _process_task(self, task: TaskItem):
        """
        Process a single task through the three-stage pipeline.

        Args:
            task: The task to process
        """
        task.status = TaskStatus.RUNNING
        task_id_short = task.id.hex[:8]

        try:
            self._emit_ui_event("status", task.id, f"[{task_id_short}] status → RUNNING")

            # Setup directories
            project_root = task.project_root.resolve()
            tests_dir = project_root / "test_bugfix"
            artifacts_dir = project_root / ".claude_tasks" / f"item_{task.id.hex}"

            # Create directories
            tests_dir.mkdir(parents=True, exist_ok=True)
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            # Step files
            step1_file = artifacts_dir / "step1.md"
            step2_file = artifacts_dir / "step2.md"
            step3_file = artifacts_dir / "step3.md"

            # Initialize Claude client
            client = ClaudeClient(project_root)


            # Step 1: Scope and analyze
            await self._execute_step1(client, task, step1_file, task_id_short)

            # Step 2: Generate failing tests
            await self._execute_step2(client, task, step1_file, tests_dir, step2_file, task_id_short)

            # Step 3: Fix and run iteratively
            await self._execute_step3(client, task, tests_dir, step3_file, step1_file, step2_file, task_id_short)

        except Exception as e:
            logger.error(f"Task {task_id_short} failed: {e}")
            task.status = TaskStatus.FAILED
            self._emit_ui_event("error", task.id, f"[{task_id_short}] ❌ failed: {str(e)}")

    async def _execute_step1(self, client: ClaudeClient, task: TaskItem, step1_file: Path, task_id_short: str):
        """Execute Step 1: Scope and analyze."""
        self._emit_ui_event("step", task.id, f"[{task_id_short}] step 1: Analyzing scope...")

        prompt = step1_prompt(str(task.project_root), task.description)
        output = await client.run(prompt)

        step1_file.write_text(output, encoding="utf-8")
        self._emit_ui_event("step_complete", task.id, f"[{task_id_short}] step 1: ✅ analysis complete")

    async def _execute_step2(self, client: ClaudeClient, task: TaskItem, step1_file: Path,
                           tests_dir: Path, step2_file: Path, task_id_short: str):
        """Execute Step 2: Generate failing tests."""
        self._emit_ui_event("step", task.id, f"[{task_id_short}] step 2: Generating failing tests...")

        prompt = step2_prompt(str(step1_file), str(tests_dir))
        output, sentinel_found = await client.run_with_sentinel(prompt, STEP2_SENTINEL)

        step2_file.write_text(output, encoding="utf-8")

        if sentinel_found:
            self._emit_ui_event("step_complete", task.id, f"[{task_id_short}] step 2: ✅ tests written")
        else:
            self._emit_ui_event("warning", task.id, f"[{task_id_short}] step 2: ⚠️ sentinel missing, continuing")

    async def _execute_step3(self, client: ClaudeClient, task: TaskItem, tests_dir: Path,
                           step3_file: Path, step1_file: Path, step2_file: Path, task_id_short: str):
        """Execute Step 3: Fix and run iteratively."""
        self._emit_ui_event("step", task.id, f"[{task_id_short}] step 3: Fixing and running tests...")

        attempt_logs = []
        passed = False

        for attempt in range(1, self.max_attempts + 1):
            self._emit_ui_event("attempt", task.id, f"[{task_id_short}] step 3: attempt {attempt}/{self.max_attempts}")

            prompt = step3_prompt(str(tests_dir), str(step1_file), str(step2_file), attempt, self.max_attempts)
            output, sentinel_found = await client.run_with_sentinel(prompt, PASS_SENTINEL)

            attempt_logs.append(f"--- Attempt {attempt} ---\n{output}\n")

            if sentinel_found:
                passed = True
                break

        # Write all attempts to step3.md
        step3_file.write_text("".join(attempt_logs), encoding="utf-8")

        if passed:
            task.status = TaskStatus.COMPLETED
            self._emit_ui_event("completed", task.id, f"[{task_id_short}] ✅ done: RESULT: PASS")
        else:
            task.status = TaskStatus.FAILED
            self._emit_ui_event("failed", task.id, f"[{task_id_short}] ❌ failed: max attempts reached")


async def run_manager_in_thread(ui_queue: Queue, manager_queue: asyncio.Queue):
    """
    Run the task manager in a separate thread.

    Args:
        ui_queue: Queue for UI events
        manager_queue: Queue for receiving tasks
    """
    manager = TaskManager(ui_queue)
    manager.start()

    try:
        while True:
            try:
                task = await asyncio.wait_for(manager_queue.get(), timeout=1.0)
                await manager.add_task(task)
            except asyncio.TimeoutError:
                continue
    finally:
        await manager.stop()