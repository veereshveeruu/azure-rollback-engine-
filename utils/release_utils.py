import os

def get_release_id():
    """
    Returns the Azure DevOps Release ID.
    Falls back to LOCAL if not available.
    """
    return os.getenv("RELEASE_ID", "LOCAL")