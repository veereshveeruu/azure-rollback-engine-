import os
import hashlib
from typing import Dict, List, Optional

# =========================================================
# CONFIG (Enterprise Standard)
# =========================================================

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "logs",
    ".venv",
    "node_modules",
    ".idea"
}

IGNORE_FILES = {
    ".DS_Store",
    "thumbs.db"
}


# =========================================================
# STEP 1: HASH SINGLE FILE (binary-safe)
# =========================================================

def hash_file(file_path: str) -> str:
    sha = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)

    return sha.hexdigest()


# =========================================================
# STEP 2: COLLECT FILES (deterministic)
# =========================================================

def collect_files(repo_path: str) -> List[str]:
    files = []

    for root, dirs, filenames in os.walk(repo_path):

        # remove ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in filenames:
            if file in IGNORE_FILES:
                continue

            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, repo_path)

            files.append(relative_path)

    # IMPORTANT: deterministic ordering
    return sorted(files)


# =========================================================
# STEP 3: BUILD REPO SNAPSHOT MAP
# =========================================================

def build_snapshot(repo_path: str) -> Dict[str, str]:

    file_map = {}

    for file in collect_files(repo_path):
        full_path = os.path.join(repo_path, file)
        file_map[file] = hash_file(full_path)

    return file_map

import json

def save_sha_snapshot(file_path: str, data: dict):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_sha_snapshot(file_path: str):
    import os
    import json

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
# =========================================================
# STEP 4: GENERATE ENTERPRISE SHA (CORE LOGIC)
# =========================================================

def generate_repo_sha256(repo_path: str) -> str:

    snapshot = build_snapshot(repo_path)

    sha = hashlib.sha256()

    # deterministic iteration
    for file_path in sorted(snapshot.keys()):

        file_hash = snapshot[file_path]

        # strict structured input
        sha.update(file_path.encode("utf-8"))
        sha.update(b":")
        sha.update(file_hash.encode("utf-8"))
        sha.update(b";")

    return sha.hexdigest()


# =========================================================
# STEP 5: AUDIT SNAPSHOT (ENTERPRISE EXPLANATION LAYER)
# =========================================================

def create_audit_snapshot(repo_path: str) -> Dict:

    snapshot = build_snapshot(repo_path)
    repo_sha = generate_repo_sha256(repo_path)

    return {
        "repository_sha": repo_sha,
        "file_count": len(snapshot),
        "files": snapshot
    }


# =========================================================
# STEP 6: COMPARE SHAS (CLEAN AUDIT LOG)
# =========================================================

def compare_sha(sha_before: str, sha_after: str):

    print("\n========== SHA VALIDATION ==========")
    print(f"SHA BEFORE : {sha_before}")
    print(f"SHA AFTER  : {sha_after}")

    if sha_before == sha_after:
        print("STATUS: NO CHANGE (Repository is identical)")
    else:
        print("STATUS: CHANGED (Repository modified)")

    print("====================================\n")