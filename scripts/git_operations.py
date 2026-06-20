import subprocess
import os
import logging
from typing import List, Dict

# -----------------------------
# CONFIG
# -----------------------------
GIT_REPO_URL = os.getenv("GIT_REPO_URL")  # https://github.com/org/repo.git
LOCAL_REPO_PATH = os.getenv("LOCAL_REPO_PATH", "/tmp/repo")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# -----------------------------
# AUTH FIX (IMPORTANT)
# -----------------------------
if GITHUB_TOKEN and GIT_REPO_URL:
    GIT_REPO_URL = GIT_REPO_URL.replace(
        "https://",
        f"https://x-access-token:{GITHUB_TOKEN}@"
    )

# -----------------------------
# SAFE SHELL EXECUTOR
# -----------------------------
def run_cmd(cmd: List[str], cwd: str = None):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True
        )

        logging.info(result.stdout)
        return result.stdout

    except subprocess.CalledProcessError as e:
        logging.error(e.stderr)
        raise Exception(f"Command failed: {' '.join(cmd)}\n{e.stderr}")


# -----------------------------
# STEP 1: CLONE REPO
# -----------------------------
def clone_repo():
    if os.path.exists(LOCAL_REPO_PATH):
        logging.info("Repo already exists. Skipping clone.")
        return

    logging.info("Cloning repository...")

    run_cmd([
        "git",
        "clone",
        GIT_REPO_URL,
        LOCAL_REPO_PATH
    ])


# -----------------------------
# STEP 2: CONFIGURE GIT USER
# -----------------------------
def configure_git_user():
    run_cmd([
        "git",
        "config",
        "--global",
        "user.email",
        "github-actions@github.com"
    ])

    run_cmd([
        "git",
        "config",
        "--global",
        "user.name",
        "github-actions[bot]"
    ])


# -----------------------------
# STEP 3: RESET TO LATEST MAIN
# -----------------------------
def reset_to_main():
    """
    Ensure repo is clean and synced with remote main
    """
    run_cmd(["git", "fetch", "origin"], cwd=LOCAL_REPO_PATH)

    run_cmd(["git", "checkout", "origin/main"], cwd=LOCAL_REPO_PATH)

    run_cmd(["git", "checkout", "-B", "main"], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 4: CREATE ROLLBACK BRANCH
# -----------------------------
def create_rollback_branch(branch_name: str):
    logging.info(f"Creating rollback branch: {branch_name}")

    run_cmd(["git", "checkout", "-b", branch_name], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 5: CHECK CLEAN STATE
# -----------------------------
def ensure_clean_state():
    status = run_cmd(["git", "status", "--porcelain"], cwd=LOCAL_REPO_PATH)

    if status.strip():
        raise Exception("Working directory is not clean. Abort rollback.")


# -----------------------------
# STEP 6: CHECKOUT BRANCH (optional)
# -----------------------------
def checkout_branch(branch_name: str):
    logging.info(f"Checking out branch: {branch_name}")

    run_cmd(["git", "checkout", branch_name], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 7: REVERT SINGLE COMMIT
# -----------------------------
def revert_commit(commit_sha: str):
    logging.info(f"Reverting commit: {commit_sha}")

    try:
        run_cmd(
            ["git", "revert", "--no-edit", commit_sha],
            cwd=LOCAL_REPO_PATH
        )

        status = run_cmd(["git", "status", "--porcelain"], cwd=LOCAL_REPO_PATH)

        if (
            "UU" in status
            or "AA" in status
            or "DD" in status
            or "conflict" in status.lower()
        ):
            logging.error(f"Merge conflict detected in {commit_sha}")

            run_cmd(["git", "revert", "--abort"], cwd=LOCAL_REPO_PATH)

            raise Exception(f"MERGE CONFLICT in {commit_sha}")

    except Exception as e:
        logging.exception(f"Revert failed: {commit_sha}")
        raise e


# -----------------------------
# STEP 8: REVERT ENGINE
# -----------------------------
def revert_commits(commits: List[Dict]):
    logging.info("Starting revert engine...")

    ordered = sorted(commits, key=lambda x: x["date"], reverse=True)

    for commit in ordered:
        sha = commit["sha"]

        try:
            revert_commit(sha)

        except Exception as e:
            logging.error(f"Rollback stopped at {sha}")
            raise Exception(f"Rollback failed at {sha}")


# -----------------------------
# STEP 9: COMMIT CHANGES (WITH CI SKIP)
# -----------------------------
def commit_revert_changes(message: str):
    status = run_cmd(["git", "status", "--porcelain"], cwd=LOCAL_REPO_PATH)

    if not status.strip():
        logging.warning("Nothing to commit after revert.")
        return

    run_cmd(["git", "add", "-A"], cwd=LOCAL_REPO_PATH)

    run_cmd([
        "git",
        "config",
        "user.email",
        "github-actions@github.com"
    ], cwd=LOCAL_REPO_PATH)

    run_cmd([
        "git",
        "config",
        "user.name",
        "github-actions[bot]"
    ], cwd=LOCAL_REPO_PATH)

    commit_message = f"{message} [skip ci]"

    run_cmd([
        "git",
        "commit",
        "-m",
        commit_message
    ], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 10: PUSH BRANCH
# -----------------------------
def push_branch(branch_name: str):
    logging.info(f"Pushing branch: {branch_name}")

    run_cmd([
        "git",
        "push",
        "-u",
        "origin",
        branch_name
    ], cwd=LOCAL_REPO_PATH)