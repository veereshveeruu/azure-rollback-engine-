import os
import subprocess
import logging
from typing import List, Dict

# -----------------------------
# CONFIG
# -----------------------------
GIT_REPO_URL = os.getenv("GIT_REPO_URL")  # https://github.com/org/repo.git
LOCAL_REPO_PATH = os.getenv("LOCAL_REPO_PATH", "/tmp/repo")


# -----------------------------
# SAFE SHELL EXECUTOR
# -----------------------------
def run_cmd(cmd: List[str], cwd: str = None):
    """
    Executes shell commands safely and logs output
    """
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
    """
    Clone repo if not already present
    """
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
# STEP 2: CREATE ROLLBACK BRANCH
# -----------------------------
def create_rollback_branch(branch_name: str):
    """
    Create a new rollback branch from main/master
    """

    logging.info(f"Creating rollback branch: {branch_name}")

    run_cmd(["git", "checkout", "main"], cwd=LOCAL_REPO_PATH)

    run_cmd(["git", "pull"], cwd=LOCAL_REPO_PATH)

    run_cmd(["git", "checkout", "-b", branch_name], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 3: CHECKOUT BRANCH (if needed)
# -----------------------------
def checkout_branch(branch_name: str):
    """
    Checkout existing branch safely
    """

    logging.info(f"Checking out branch: {branch_name}")

    run_cmd(["git", "checkout", branch_name], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 4: CHECK CLEAN WORKING DIRECTORY
# -----------------------------
def ensure_clean_state():
    """
    Prevent accidental dirty state
    """

    status = run_cmd(["git", "status", "--porcelain"], cwd=LOCAL_REPO_PATH)

    if status.strip():
        raise Exception("Working directory is not clean. Abort rollback.")


# -----------------------------
# STEP 5: REVERT SINGLE COMMIT
# -----------------------------
def revert_commit(commit_sha: str):
    """
    Revert a single commit safely
    """

    logging.info(f"Reverting commit: {commit_sha}")

    try:
        # Perform revert without auto commit first (safe check)
        run_cmd(["git", "revert", "--no-edit", commit_sha], cwd=LOCAL_REPO_PATH)

    except Exception as e:
        logging.error(f"Revert failed for {commit_sha}")

        # Check conflict state
        status = run_cmd(["git", "status"], cwd=LOCAL_REPO_PATH)

        if "unmerged" in status or "conflict" in status.lower():
            raise Exception(f"MERGE CONFLICT detected in commit {commit_sha}")

        raise e


# -----------------------------
# STEP 6: REVERT ENGINE (CORE LOGIC)
# -----------------------------
def revert_commits(commits: List[Dict]):
    """
    Revert commits in correct order:
    latest → oldest
    """

    logging.info("Starting revert engine...")

    # Ensure correct order (IMPORTANT requirement)
    ordered = sorted(commits, key=lambda x: x["date"], reverse=True)

    for commit in ordered:
        sha = commit["sha"]

        logging.info(f"Reverting: {sha}")

        try:
            revert_commit(sha)

        except Exception as e:
            logging.error(f"Stopping rollback due to error: {str(e)}")
            raise Exception(f"Rollback stopped at commit {sha}")


# -----------------------------
# STEP 7: FINAL COMMIT AFTER REVERT
# -----------------------------
def commit_revert_changes(message: str):
    """
    Commit all revert changes
    """

    run_cmd(["git", "add", "."], cwd=LOCAL_REPO_PATH)

    run_cmd(["git", "commit", "-m", message], cwd=LOCAL_REPO_PATH)


# -----------------------------
# STEP 8: PUSH BRANCH
# -----------------------------
def push_branch(branch_name: str):
    """
    Push rollback branch to remote
    """

    logging.info(f"Pushing branch: {branch_name}")

    run_cmd([
        "git",
        "push",
        "-u",
        "origin",
        branch_name
    ], cwd=LOCAL_REPO_PATH)