# logging_config.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026

"""Logger configuration for dcmpress (console plus rotating file handler)."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "dcmpress"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "dcmpress.log"

def configure_logger() -> logging.Logger:
    """Configure and return the application logger.

    Logs are emitted to the console and to a rotating log file under ``logs/``.
    The level is read from the ``LOG_LEVEL`` environment variable (default
    ``INFO``). Streamlit reruns the script after user interaction, so this
    function avoids adding duplicate handlers on each rerun. Patient identifiers
    are never logged.

    Returns
    -------
    logging.Logger
        Configured logger for the dcmpress app.
    """
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(log_level)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

LOGGER = configure_logger()