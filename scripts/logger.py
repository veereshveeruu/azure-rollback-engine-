import logging
import os
from datetime import datetime

# -----------------------------
# LOG DIRECTORY
# -----------------------------
LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)


# -----------------------------
# CREATE RUN LOG FILE
# -----------------------------
def get_log_file():
    """
    Each run gets its own log file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"rollback_{timestamp}.log")


# -----------------------------
# LOGGER FACTORY
# -----------------------------
def setup_logger(name: str = "rollback-engine"):
    """
    Central logger configuration
    """

    logger = logging.getLogger(name)

    # Avoid duplicate handlers (important in scripts)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_file = get_log_file()

    # -------------------------
    # FORMATTER
    # -------------------------
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # -------------------------
    # FILE HANDLER
    # -------------------------
    file_handler = logging.FileHandler(
    log_file,
    encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # -------------------------
    # CONSOLE HANDLER
    # -------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Attach handlers
    logger.addHandler(file_handler)
    return logger