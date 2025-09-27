"""
Main PySide6 GUI window for the Fixit.
"""
import asyncio
import logging
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QRadioButton,
    QButtonGroup, QGroupBox, QFileDialog, QMessageBox, QSplitter, QFrame,
    QScrollArea
)
from PySide6.QtCore import QTimer, Qt, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor, QTextCursor

from core.models import TaskItem, TaskType, UiEvent
from core.manager import run_manager_in_thread


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main GUI window for the Fixit."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        self.setWindowTitle("Fixit")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)

        # Queues for communication
        self.ui_queue = Queue()
        self.manager_queue: Optional[asyncio.Queue] = None

        # Manager thread
        self.manager_thread: Optional[threading.Thread] = None
        self.manager_loop: Optional[asyncio.AbstractEventLoop] = None

        # GUI components
        self.project_root_line_edit: Optional[QLineEdit] = None
        self.bug_radio: Optional[QRadioButton] = None
        self.feature_radio: Optional[QRadioButton] = None
        self.task_type_group: Optional[QButtonGroup] = None
        self.description_text: Optional[QTextEdit] = None
        self.log_text: Optional[QTextEdit] = None

        self._setup_modern_theme()
        self._setup_gui()
        self._start_manager_thread()
        self._start_ui_update_timer()

    def _setup_modern_theme(self):
        """Set up OpenAI-style modern theme with light grey colors."""
        # OpenAI-inspired color palette
        self.colors = {
            'background': '#fafafa',           # Very light grey background
            'surface': '#ffffff',             # White surface
            'surface_alt': '#f7f7f8',         # Alternative surface
            'border': '#e5e5e5',              # Light border
            'border_hover': '#d1d5db',        # Border hover
            'text_primary': '#1f2937',        # Dark grey text
            'text_secondary': '#6b7280',      # Medium grey text
            'text_muted': '#9ca3af',          # Light grey text
            'accent': '#10a37f',              # OpenAI green
            'accent_hover': '#0d8f6a',        # Darker green
            'danger': '#ef4444',              # Red for cancel
            'danger_hover': '#dc2626',        # Darker red
            'input_bg': '#ffffff',            # Input background
            'input_border': '#d1d5db',        # Input border
            'sidebar': '#f9fafb',             # Sidebar background
        }

        # Set application-wide stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            }}
        """)

    def _setup_gui(self):
        """Set up the modern GUI layout."""
        # Central widget with background
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {self.colors['background']};")
        self.setCentralWidget(central_widget)

        # Main layout without margins for full coverage
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar panel
        left_panel = self._create_left_panel()

        # Right content panel
        right_panel = self._create_right_panel()

        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def _create_left_panel(self):
        """Create the modern left configuration panel."""
        # Main container
        container = QFrame()
        container.setFixedWidth(380)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['sidebar']};
                border-right: 1px solid {self.colors['border']};
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Header
        header = QLabel("Fixit")
        header.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 8px;
            }}
        """)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("Automated debugging with Claude Code")
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_secondary']};
                font-size: 14px;
                margin-bottom: 16px;
            }}
        """)
        layout.addWidget(subtitle)

        # Project root section
        layout.addWidget(self._create_project_section())

        # Task type section
        layout.addWidget(self._create_task_type_section())

        # Description section
        layout.addWidget(self._create_description_section())

        # Action buttons
        layout.addWidget(self._create_action_buttons())

        # Spacer to push everything to top
        layout.addStretch()

        return container

    def _create_project_section(self):
        """Create the project root selection section."""
        section = QFrame()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        label = QLabel("Project Root")
        label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 4px;
            }}
        """)
        layout.addWidget(label)

        # Input container
        input_container = QFrame()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        # Path input
        self.project_root_line_edit = QLineEdit()
        self.project_root_line_edit.setPlaceholderText("Select project directory...")
        self.project_root_line_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['input_bg']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                color: {self.colors['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {self.colors['accent']};
                outline: none;
            }}
        """)

        # Browse button
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_project_root)
        browse_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['surface']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 500;
                color: {self.colors['text_primary']};
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['surface_alt']};
                border-color: {self.colors['border_hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['border']};
            }}
        """)

        input_layout.addWidget(self.project_root_line_edit)
        input_layout.addWidget(browse_button)
        layout.addWidget(input_container)

        return section

    def _create_task_type_section(self):
        """Create the task type selection section."""
        section = QFrame()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Label
        label = QLabel("Task Type")
        label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 14px;
                font-weight: 500;
            }}
        """)
        layout.addWidget(label)

        # Radio buttons container
        radio_container = QFrame()
        radio_layout = QHBoxLayout(radio_container)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(16)

        # Radio buttons with modern styling
        self.bug_radio = QRadioButton("Bug Fix")
        self.feature_radio = QRadioButton("Feature Test")
        self.bug_radio.setChecked(True)

        for radio in [self.bug_radio, self.feature_radio]:
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {self.colors['text_primary']};
                    font-size: 14px;
                    spacing: 8px;
                }}
                QRadioButton::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 2px solid {self.colors['input_border']};
                    background-color: {self.colors['surface']};
                }}
                QRadioButton::indicator:checked {{
                    border-color: {self.colors['accent']};
                    background-color: {self.colors['accent']};
                }}
                QRadioButton::indicator:checked::after {{
                    content: '';
                    width: 6px;
                    height: 6px;
                    border-radius: 3px;
                    background-color: white;
                    margin: 3px;
                }}
            """)

        self.task_type_group = QButtonGroup()
        self.task_type_group.addButton(self.bug_radio, 0)
        self.task_type_group.addButton(self.feature_radio, 1)

        radio_layout.addWidget(self.bug_radio)
        radio_layout.addWidget(self.feature_radio)
        radio_layout.addStretch()

        layout.addWidget(radio_container)
        return section

    def _create_description_section(self):
        """Create the description input section."""
        section = QFrame()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        label = QLabel("Description")
        label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 14px;
                font-weight: 500;
            }}
        """)
        layout.addWidget(label)

        # Text area
        self.description_text = QTextEdit()
        self.description_text.setPlaceholderText("Describe the bug or feature test you want Claude to work on...")
        self.description_text.setMinimumHeight(140)
        self.description_text.setMaximumHeight(200)
        self.description_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors['input_bg']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                color: {self.colors['text_primary']};
                line-height: 1.4;
            }}
            QTextEdit:focus {{
                border-color: {self.colors['accent']};
                outline: none;
            }}
        """)
        layout.addWidget(self.description_text)

        return section

    def _create_action_buttons(self):
        """Create the action buttons section."""
        section = QFrame()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Add Task button (primary)
        add_button = QPushButton("Start Debugging")
        add_button.clicked.connect(self._add_task)
        add_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['accent_hover']};
                transform: translateY(1px);
            }}
        """)

        # Cancel All button (secondary)
        cancel_button = QPushButton("Cancel All Tasks")
        cancel_button.clicked.connect(self._cancel_all)
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
                color: {self.colors['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['surface_alt']};
                border-color: {self.colors['border_hover']};
                color: {self.colors['text_primary']};
            }}
        """)

        layout.addWidget(add_button)
        layout.addWidget(cancel_button)

        return section

    def _create_right_panel(self):
        """Create the modern right log panel."""
        container = QFrame()
        container.setStyleSheet(f"background-color: {self.colors['surface']};")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Activity Log")
        title.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 18px;
                font-weight: 600;
            }}
        """)

        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Log container with modern styling
        log_container = QFrame()
        log_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['surface_alt']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
            }}
        """)

        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(1, 1, 1, 1)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors['surface_alt']};
                border: none;
                border-radius: 7px;
                padding: 16px;
                font-family: 'SF Mono', 'Monaco', 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                color: {self.colors['text_primary']};
                line-height: 1.5;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['border_hover']};
            }}
        """)

        # Add welcome message with better formatting
        welcome_msg = """Welcome to Fixit

🤖 Automated debugging powered by Claude Code
📋 Ready to process your debugging tasks
🔧 Select a project and describe your issue to get started

Waiting for your first task..."""
        self.log_text.setText(welcome_msg)

        log_layout.addWidget(self.log_text)
        layout.addWidget(log_container)

        return container

    def _browse_project_root(self):
        """Open directory picker for project root."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Project Root",
            str(Path.home()),
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.project_root_line_edit.setText(directory)

    def _add_task(self):
        """Add a new debugging task."""
        project_root = self.project_root_line_edit.text().strip()
        task_type = TaskType.BUG if self.bug_radio.isChecked() else TaskType.FEATURE_TEST
        description = self.description_text.toPlainText().strip()

        # Validation
        if not project_root:
            QMessageBox.critical(self, "Error", "Please select a project root directory.")
            return

        if not Path(project_root).exists():
            QMessageBox.critical(self, "Error", "Project root directory does not exist.")
            return

        if not description:
            QMessageBox.critical(self, "Error", "Please provide a task description.")
            return

        # Create task item
        task = TaskItem(
            project_root=Path(project_root),
            task_type=task_type,
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
                self.description_text.clear()
                self._log_message(f"Task added: {task.id.hex[:8]}")

            except Exception as e:
                logger.error(f"Failed to add task: {e}")
                QMessageBox.critical(self, "Error", f"Failed to add task: {str(e)}")

    def _cancel_all(self):
        """Cancel all pending tasks."""
        # For now, just log the action
        # In a full implementation, we would signal the manager to cancel
        self._log_message("Cancel All requested (not implemented)")
        QMessageBox.information(self, "Info", "Cancel All functionality not implemented in this version.")

    def _log_message(self, message: str):
        """Add a formatted message to the log feed."""
        import datetime

        # Get current time
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Format message with timestamp and modern styling
        formatted_message = f"[{timestamp}] {message}"

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        # If not the first message, add a newline
        if cursor.position() > 0:
            cursor.insertText("\n")

        cursor.insertText(formatted_message)
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

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
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._process_ui_events)
        self.ui_timer.start(150)  # 150ms interval

    def _process_ui_events(self):
        """Process pending UI events from the queue."""
        try:
            while True:
                event: UiEvent = self.ui_queue.get_nowait()
                self._log_message(event.payload)
        except Empty:
            pass

    def closeEvent(self, event):
        """Handle window close event."""
        # Cleanup
        if hasattr(self, 'ui_timer'):
            self.ui_timer.stop()
        if self.manager_loop:
            self.manager_loop.call_soon_threadsafe(self.manager_loop.stop)
        if self.manager_thread:
            self.manager_thread.join(timeout=1.0)
        event.accept()