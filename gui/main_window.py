"""
Main Tkinter GUI window for the Claude Debugger.
"""
import asyncio
import logging
import threading
import tkinter as tk
from pathlib import Path
from queue import Queue, Empty
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Optional

from core.models import TaskItem, TaskType, UiEvent
from core.manager import run_manager_in_thread


logger = logging.getLogger(__name__)


class MainWindow:
    """Main GUI window for the Claude Debugger."""

    def __init__(self):
        """Initialize the main window."""
        self.root = tk.Tk()
        self.root.title("Claude Debugger")
        self.root.geometry("1000x700")

        # Queues for communication
        self.ui_queue = Queue()
        self.manager_queue: Optional[asyncio.Queue] = None

        # Manager thread
        self.manager_thread: Optional[threading.Thread] = None
        self.manager_loop: Optional[asyncio.AbstractEventLoop] = None

        # GUI variables
        self.project_root_var = tk.StringVar()
        self.task_type_var = tk.StringVar(value=TaskType.BUG.value)
        self.description_text: Optional[scrolledtext.ScrolledText] = None
        self.log_text: Optional[scrolledtext.ScrolledText] = None

        self._setup_gui()
        self._start_manager_thread()
        self._start_ui_update_timer()

    def _setup_gui(self):
        """Set up the GUI layout."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Left panel
        left_frame = ttk.LabelFrame(main_frame, text="Task Configuration", padding="10")
        left_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # Project root selection
        ttk.Label(left_frame, text="Project Root:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        root_frame = ttk.Frame(left_frame)
        root_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        root_frame.columnconfigure(0, weight=1)

        self.project_root_entry = ttk.Entry(root_frame, textvariable=self.project_root_var, width=40)
        self.project_root_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        ttk.Button(root_frame, text="Browse", command=self._browse_project_root).grid(row=0, column=1)

        # Task type selection
        ttk.Label(left_frame, text="Type:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))

        type_frame = ttk.Frame(left_frame)
        type_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Radiobutton(type_frame, text="Bug", variable=self.task_type_var,
                       value=TaskType.BUG.value).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Feature Test", variable=self.task_type_var,
                       value=TaskType.FEATURE_TEST.value).grid(row=0, column=1, sticky=tk.W)

        # Description
        ttk.Label(left_frame, text="Description:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))

        self.description_text = scrolledtext.ScrolledText(left_frame, width=50, height=10, wrap=tk.WORD)
        self.description_text.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=6, column=0, sticky=(tk.W, tk.E))

        ttk.Button(button_frame, text="Add Task", command=self._add_task).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel All", command=self._cancel_all).grid(row=0, column=1)

        # Configure left frame grid weights
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(5, weight=1)

        # Right panel - Log feed
        right_frame = ttk.LabelFrame(main_frame, text="Log Feed", padding="10")
        right_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.log_text = scrolledtext.ScrolledText(right_frame, width=60, height=30, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure right frame grid weights
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

    def _browse_project_root(self):
        """Open directory picker for project root."""
        directory = filedialog.askdirectory(title="Select Project Root")
        if directory:
            self.project_root_var.set(directory)

    def _add_task(self):
        """Add a new debugging task."""
        project_root = self.project_root_var.get().strip()
        task_type = self.task_type_var.get()
        description = self.description_text.get("1.0", tk.END).strip()

        # Validation
        if not project_root:
            messagebox.showerror("Error", "Please select a project root directory.")
            return

        if not Path(project_root).exists():
            messagebox.showerror("Error", "Project root directory does not exist.")
            return

        if not description:
            messagebox.showerror("Error", "Please provide a task description.")
            return

        # Create task item
        task = TaskItem(
            project_root=Path(project_root),
            task_type=TaskType(task_type),
            description=description
        )

        # Send to manager
        if self.manager_loop and self.manager_queue:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.manager_queue.put(task),
                    self.manager_loop
                )
                future.result(timeout=1.0)

                # Clear description after successful submission
                self.description_text.delete("1.0", tk.END)
                self._log_message(f"Task added: {task.id.hex[:8]}")

            except Exception as e:
                logger.error(f"Failed to add task: {e}")
                messagebox.showerror("Error", f"Failed to add task: {str(e)}")

    def _cancel_all(self):
        """Cancel all pending tasks."""
        # For now, just log the action
        # In a full implementation, we would signal the manager to cancel
        self._log_message("Cancel All requested (not implemented)")
        messagebox.showinfo("Info", "Cancel All functionality not implemented in this version.")

    def _log_message(self, message: str):
        """Add a message to the log feed."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _start_manager_thread(self):
        """Start the background manager thread."""
        def run_manager():
            """Run the manager in a separate thread with its own event loop."""
            self.manager_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.manager_loop)

            self.manager_queue = asyncio.Queue()

            try:
                self.manager_loop.run_until_complete(
                    run_manager_in_thread(self.ui_queue, self.manager_queue)
                )
            except Exception as e:
                logger.error(f"Manager thread error: {e}")
            finally:
                self.manager_loop.close()

        self.manager_thread = threading.Thread(target=run_manager, daemon=True)
        self.manager_thread.start()

    def _start_ui_update_timer(self):
        """Start the timer to update UI from the queue."""
        self._process_ui_events()

    def _process_ui_events(self):
        """Process pending UI events from the queue."""
        try:
            while True:
                event: UiEvent = self.ui_queue.get_nowait()
                self._log_message(event.payload)
        except Empty:
            pass

        # Schedule next check
        self.root.after(150, self._process_ui_events)

    def run(self):
        """Start the GUI main loop."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup
            if self.manager_loop:
                self.manager_loop.call_soon_threadsafe(self.manager_loop.stop)
            if self.manager_thread:
                self.manager_thread.join(timeout=1.0)