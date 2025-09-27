"""
Simple test to verify project structure without external dependencies.
"""
import os
from pathlib import Path

def test_structure():
    """Test that all required files exist."""
    print("Testing project structure...")

    required_files = [
        "app.py",
        "core/__init__.py",
        "core/models.py",
        "core/manager.py",
        "core/prompts.py",
        "core/cli_strings.py",
        "claude/__init__.py",
        "claude/client.py",
        "gui/__init__.py",
        "gui/main_window.py",
        "pyproject.toml",
        ".gitignore"
    ]

    missing_files = []

    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"OK Found {file_path}")

    if missing_files:
        print(f"\nERROR Missing files: {missing_files}")
        return False

    print("\nAll required files present!")

    # Test directory structure
    required_dirs = ["core", "claude", "gui"]
    for dir_name in required_dirs:
        if not Path(dir_name).is_dir():
            print(f"ERROR Missing directory: {dir_name}")
            return False
        else:
            print(f"OK Directory {dir_name} exists")

    print("\nProject structure is complete!")
    return True

def test_file_contents():
    """Test that key files have expected content."""
    print("\nTesting file contents...")

    # Test pyproject.toml has correct name
    pyproject_content = Path("pyproject.toml").read_text()
    if 'name = "claude-debugger"' in pyproject_content:
        print("OK pyproject.toml has correct project name")
    else:
        print("ERROR pyproject.toml missing correct project name")
        return False

    # Test app.py has main function
    app_content = Path("app.py").read_text()
    if "def main():" in app_content:
        print("OK app.py has main function")
    else:
        print("ERROR app.py missing main function")
        return False

    # Test core modules have expected classes/functions
    models_content = Path("core/models.py").read_text()
    if "class TaskItem" in models_content:
        print("OK core/models.py has TaskItem class")
    else:
        print("ERROR core/models.py missing TaskItem class")
        return False

    print("\nFile contents look good!")
    return True

if __name__ == "__main__":
    structure_ok = test_structure()
    contents_ok = test_file_contents()

    if structure_ok and contents_ok:
        print("\nSUCCESS: Project structure and contents are valid!")
        exit(0)
    else:
        print("\nERROR: Project structure or contents have issues!")
        exit(1)