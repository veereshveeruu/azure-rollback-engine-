import time
import functools
import logging
from datetime import datetime


# -----------------------------
# RETRY DECORATOR (VERY IMPORTANT)
# -----------------------------
def retry(max_retries=3, delay=2, exceptions=(Exception,)):
    """
    Generic retry decorator for API calls and git commands
    """
    
    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            attempt = 0

            while attempt < max_retries:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    attempt += 1
                    logging.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_retries}): {str(e)}"
                    )

                    if attempt == max_retries:
                        logging.error(f"{func.__name__} failed permanently")
                        raise

                    time.sleep(delay)

        return wrapper

    return decorator

import os

def get_env(key: str, required: bool = True, default=None):
    value = os.getenv(key, default)

    if required and not value:
        raise Exception(f"Missing required environment variable: {key}")

    return value
# -----------------------------
# TIMESTAMP UTIL
# -----------------------------
def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -----------------------------
# SAFE STRING CLEANER
# -----------------------------
def safe_string(value: str):
    if value is None:
        return ""
    return str(value).strip()


# -----------------------------
# VALIDATE PR NUMBER
# -----------------------------
def is_valid_pr_number(pr_number):
    try:
        return int(pr_number) > 0
    except:
        return False


# -----------------------------
# EXTRACT PR NUMBER FROM URL
# -----------------------------
def extract_pr_number_from_url(url: str):
    try:
        return url.rstrip("/").split("/")[-1]
    except Exception:
        raise Exception(f"Invalid PR URL: {url}")


# -----------------------------
# LOG STEP HELPER
# -----------------------------
def log_step(logger, step_name: str, message: str):
    logger.info(f"[{step_name}] {message}")