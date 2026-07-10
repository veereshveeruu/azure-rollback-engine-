import logging
import os
from datetime import datetime


LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)


def get_log_file() -> str:
    """
    Creates one log file per day.
    Example:
    logs/rollback_2026-07-08.log
    """

    date = datetime.now().strftime("%Y-%m-%d")

    return os.path.join(
        LOG_DIR,
        f"rollback_{date}.log"
    )


def setup_logger(name: str = "rollback-engine") -> logging.Logger:
    """
    Configure rollback engine logger.
    """

    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False


    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


    # Daily log file
    file_handler = logging.FileHandler(
        get_log_file(),
        encoding="utf-8"
    )

    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)


    # Console output
    console_handler = logging.StreamHandler()

    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)


    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


    return logger