"""
Logging configuration.

Every script imports `get_logger(__name__)` and writes structured logs
to both console and `output/logs/<run_id>.log`. Run IDs are timestamp-based.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from config.settings import OUTPUT_LOGS, LOG_FORMAT, LOG_LEVEL


_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
_LOG_FILE = OUTPUT_LOGS / f"{_RUN_ID}.log"


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger that writes to console and the per-run file.

    Loggers are cached by name; safe to call repeatedly.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(LOG_FORMAT)

    OUTPUT_LOGS.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(_LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def current_log_path() -> Path:
    """Path of the active run's log file. Useful for debugging."""
    return _LOG_FILE
