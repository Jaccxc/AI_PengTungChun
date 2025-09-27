"""
Main entrypoint for the Claude Debugger application.
"""
import logging
import sys
from pathlib import Path

from gui import MainWindow


def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path.home() / "AppData" / "Local" / "ClaudeDebugger"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Claude Debugger...")

    try:
        # Create and run the main window
        app = MainWindow()
        app.run()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        logger.info("Claude Debugger shutting down")


if __name__ == "__main__":
    main()