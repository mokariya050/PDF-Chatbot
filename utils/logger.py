"""
Logger Module
=============

Provides a centralized, reusable logging setup for the entire application.

Why a dedicated logger module?
    - Consistent log format across all modules.
    - Logs go to BOTH console (for development) and file (for debugging).
    - Rotating file handler prevents log files from growing forever.
    - Each module gets its own named logger for granular filtering.

Usage:
    from utils.logger import get_logger

    logger = get_logger(__name__)

    logger.info("PDF loaded successfully")
    logger.error("Failed to connect to Gemini API")
    logger.debug("Chunk 47: 'The quick brown fox...'")

Why __name__?
    Python's __name__ variable contains the module's import path.
    For utils/pdf_loader.py, __name__ == "utils.pdf_loader".
    This means each log line shows WHICH module produced it —
    invaluable when debugging across 10+ files.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings


# ----------------------------------------------------------------
# Constants
# ----------------------------------------------------------------
# Log format: timestamp | level | module name | message
# This format is optimized for readability and grep-ability.
# You can grep for "ERROR" to find all errors, or "pdf_loader"
# to find all logs from the PDF loading module.
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"

# Date format: YYYY-MM-DD HH:MM:SS (ISO 8601 inspired, human-readable)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log file configuration
LOG_FILE_NAME = "app.log"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per log file
LOG_FILE_BACKUP_COUNT = 3  # Keep 3 rotated backups (app.log.1, .2, .3)


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Create and return a configured logger instance.

    This is a FACTORY FUNCTION — it creates logger objects.
    Each module calls this once with its __name__ to get a logger
    that identifies which module produced each log message.

    How it works internally:
        1. logging.getLogger(name) either creates a new logger or
           returns an existing one with that name (loggers are cached
           by Python's logging module — another singleton pattern!).
        2. We check if handlers already exist to avoid adding
           duplicate handlers on repeated calls (defensive programming).
        3. We attach a console handler (StreamHandler) for real-time
           feedback during development.
        4. We attach a rotating file handler for persistent logs
           that survive application restarts.
        5. We set the formatter on both handlers for consistent output.

    Args:
        name: Logger name — use __name__ for automatic module identification.
            Example: "utils.pdf_loader" → logs show which module produced them.
        level: Minimum log level to capture. Default is DEBUG (capture everything).
            In production, you might set this to logging.INFO to reduce noise.

    Returns:
        logging.Logger: Configured logger instance ready to use.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("PDF loaded: 12 pages")
        2026-06-28 13:30:45 | INFO     | utils.pdf_loader     | PDF loaded: 12 pages
    """
    # Get or create a logger with the given name.
    # Python's logging module caches loggers by name, so calling
    # getLogger("utils.pdf_loader") twice returns the SAME object.
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Guard: If this logger already has handlers, it was already
    # configured. Skip setup to prevent duplicate log lines.
    # This happens when a module is imported multiple times.
    if logger.handlers:
        return logger

    # --- Create the log formatter ---
    # The formatter defines HOW each log line looks.
    # We use the same format for both console and file.
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )

    # --- Handler 1: Console (StreamHandler) ---
    # Sends log messages to sys.stdout (the terminal).
    # Great for real-time feedback during development.
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.INFO)  # Console shows INFO and above
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Handler 2: Rotating File (RotatingFileHandler) ---
    # Writes logs to a file for persistent debugging.
    #
    # Why "rotating"?
    #   Without rotation, log files grow forever. A busy app can
    #   generate gigabytes of logs. RotatingFileHandler automatically:
    #   1. Writes to app.log until it hits LOG_FILE_MAX_BYTES (5 MB).
    #   2. Renames app.log → app.log.1 (and .1 → .2, .2 → .3).
    #   3. Starts a fresh app.log.
    #   4. Deletes the oldest backup when LOG_FILE_BACKUP_COUNT is exceeded.
    #
    # Result: You always have the latest ~20 MB of logs (5 MB × 4 files).
    try:
        log_file_path = settings.LOG_DIR / LOG_FILE_NAME

        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",  # Handle non-ASCII characters in PDFs
        )
        file_handler.setLevel(logging.DEBUG)  # File captures EVERYTHING
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # If we can't write to the log file (permissions, disk full, etc.),
        # log a warning to console but DON'T crash the app.
        # Logging is important, but not worth killing the application over.
        logger.warning(f"Could not set up file logging: {e}")

    return logger


# ----------------------------------------------------------------
# Module-level self-test
# ----------------------------------------------------------------
if __name__ == "__main__":
    # Quick test: create a logger and emit messages at each level.
    test_logger = get_logger("test_logger")

    print("=" * 70)
    print("📝 Logger Module — Self Test")
    print("=" * 70)

    test_logger.debug("This is a DEBUG message (file only, not console)")
    test_logger.info("This is an INFO message (console + file)")
    test_logger.warning("This is a WARNING message (console + file)")
    test_logger.error("This is an ERROR message (console + file)")
    test_logger.critical("This is a CRITICAL message (console + file)")

    print("=" * 70)
    print(f"✅ Log file written to: {settings.LOG_DIR / LOG_FILE_NAME}")
    print("   Check the file to see the DEBUG message too!")
    print("=" * 70)
