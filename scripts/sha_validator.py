import os
import hashlib
from typing import Dict, List

# -----------------------------
# CONFIG
# -----------------------------
IGNORE_DIRS = {".git", "__pycache__", "logs"}
IGNORE_FILES = {".DS_Store"}


# -----------------------------
# STEP 1: HASH SINGLE FILE
# -----------------------------
def hash_file(file_path: str) -> str:
    """
    Returns SHA256 of a single file
    """
    sha = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha.update(chunk)

        return sha.hexdigest()

    except Exception as e:
        raise Exception(f"Failed to hash file {file_path}: {str(e)}")


# -----------------------------
# STEP 2: COLLECT ALL FILES
# -----------------------------
def collect_files(repo_path: str) -> List[str]:
    """
    Collect all files excluding ignored folders/files
    """

    all_files = []

    for root, dirs, files in os.walk(repo_path):

        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file in IGNORE_FILES:
                continue

            full_path = os.path.join(root, file)
            all_files.append(full_path)

    return all_files


# -----------------------------
# STEP 3: BUILD DETERMINISTIC HASH MAP
# -----------------------------
def build_file_hash_map(repo_path: str) -> Dict[str, str]:
    """
    Create sorted file → hash mapping
    """

    files = collect_files(repo_path)

    file_hash_map = {}

    for file_path in files:
        relative_path = os.path.relpath(file_path, repo_path)
        file_hash_map[relative_path] = hash_file(file_path)

    # Ensure deterministic order
    return dict(sorted(file_hash_map.items()))


# -----------------------------
# STEP 4: GENERATE GLOBAL SHA256
# -----------------------------
def generate_repo_sha256(repo_path: str) -> str:
    """
    Create a single SHA256 representing entire repo state
    """

    file_map = build_file_hash_map(repo_path)

    combined = hashlib.sha256()

    for file_path, file_hash in file_map.items():
        combined.update(file_path.encode())
        combined.update(file_hash.encode())

    return combined.hexdigest()


# -----------------------------
# STEP 5: SAVE SNAPSHOT
# -----------------------------
def save_sha_snapshot(file_path: str, sha_value: str):
    """
    Save SHA to file (before/after tracking)
    """

    with open(file_path, "w") as f:
        f.write(sha_value)


# -----------------------------
# STEP 6: LOAD SNAPSHOT
# -----------------------------
def load_sha_snapshot(file_path: str) -> str:
    """
    Read saved SHA snapshot
    """

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        return f.read().strip()


# -----------------------------
# STEP 7: COMPARE SHA VALUES
# -----------------------------
def compare_sha(before: str, after: str) -> bool:
    """
    Validate rollback success
    """

    if not before or not after:
        raise Exception("Missing SHA values for comparison")

    return before == after