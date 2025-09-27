"""
Test script to verify all imports work correctly.
"""
import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported without errors."""
    try:
        print("Testing imports...")

        # Test core imports
        from core import TaskItem, TaskType, TaskStatus, UiEvent
        print("OK Core models imported successfully")

        from core import step1_prompt, step2_prompt, step3_prompt
        print("OK Core prompts imported successfully")

        from core import STEP2_SENTINEL, PASS_SENTINEL, FAIL_SENTINEL
        print("OK Core constants imported successfully")

        # Test Claude client
        from claude import ClaudeClient, ClaudeCLIError
        print("OK Claude client imported successfully")

        # Test GUI (this might fail without tkinter but let's try)
        try:
            from gui import MainWindow
            print("OK GUI imported successfully")
        except ImportError as e:
            print(f"WARNING GUI import failed (expected if tkinter not available): {e}")

        # Test basic functionality
        task = TaskItem(
            project_root=Path("."),
            task_type=TaskType.BUG,
            description="Test task"
        )
        print(f"OK Created test task: {task.id.hex[:8]}")

        prompt = step1_prompt("/test/path", "Test description")
        print(f"OK Generated step1 prompt (length: {len(prompt)})")

        print("\nAll imports successful!")
        return True

    except Exception as e:
        print(f"ERROR Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)