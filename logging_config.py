# logging_config.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026

import logging

LOGGER_NAME = "dcmpress"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def configure_logger() -> logging.Logger:
    """Configure and return the application logger.

    Streamlit reruns the script after user interaction, so this function avoids
    adding duplicate handlers on each rerun.

    Returns
    -------
    logging.Logger
        Configured logger for the dcmpress app.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

    return logger

LOGGER = configure_logger()