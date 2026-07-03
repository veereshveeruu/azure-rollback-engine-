import getpass
import os

def get_current_user():
    """
    Returns the current OS user running the script.
    """
    return (
        os.getenv("USERNAME")
        or os.getenv("USER")
        or getpass.getuser()
        or "Unknown"
    )