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

if not GIT_REPO_URL:
     raise Exception("GIT_REPO_URL is None")

if not LOCAL_REPO_PATH:
    raise Exception("LOCAL_REPO_PATH missing")
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
    logging.info(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True
    )
    # Ignore "nothing to abort" scenarios
    if (
        result.returncode != 0
        and cmd[0] == "git"
        and len(cmd) >= 3
        and cmd[1] in ["revert", "merge"]
        and cmd[2] == "--abort"
    ):
        return result.stdout

    if result.returncode != 0:
        logging.error(f"Return Code: {result.returncode}")

        if result.stdout:
            logging.error(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            logging.error(f"STDERR:\n{result.stderr}")

        raise Exception(
            f"Command failed: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return result.stdout

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

def configure_remote_auth():
    if not GITHUB_TOKEN:
        raise Exception("GITHUB_TOKEN not found")

    authenticated_url = GIT_REPO_URL

    run_cmd(
        ["git", "remote", "set-url", "origin", authenticated_url],
        cwd=LOCAL_REPO_PATH
    )

    logging.info("Updated origin remote with authenticated URL")
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

def branch_exists_local(branch_name: str) -> bool:
    result = run_cmd(
        ["git", "branch", "--list", branch_name],
        cwd=LOCAL_REPO_PATH,
    )
    return bool(result.strip())


def branch_exists_remote(branch_name: str) -> bool:
    result = run_cmd(
        ["git", "ls-remote", "--heads", "origin", branch_name],
        cwd=LOCAL_REPO_PATH,
    )
    return bool(result.strip())


def delete_local_branch(branch_name: str):
    logging.info(f"Deleting local branch: {branch_name}")

    run_cmd(
        ["git", "branch", "-D", branch_name],
        cwd=LOCAL_REPO_PATH,
    )


def delete_remote_branch(branch_name: str):
    logging.info(f"Deleting remote branch: {branch_name}")

    run_cmd(
        ["git", "push", "origin", "--delete", branch_name],
        cwd=LOCAL_REPO_PATH,
    )

def ensure_clean_rollback_branch(branch_name: str):
    run_cmd(["git", "checkout", "main"], cwd=LOCAL_REPO_PATH)
    if branch_exists_local(branch_name):
        logging.info(f"Local branch '{branch_name}' exists. Deleting...")
        delete_local_branch(branch_name)

    if branch_exists_remote(branch_name):
        logging.info(f"Remote branch '{branch_name}' exists. Deleting...")
        delete_remote_branch(branch_name)
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
    """
    Clean any leftover Git state before starting rollback.
    """

    logging.info("Ensuring repository is in a clean state...")

    # Abort any unfinished revert
    run_cmd(["git", "revert", "--abort"], cwd=LOCAL_REPO_PATH)

    # Abort any unfinished merge
    run_cmd(["git", "merge", "--abort"], cwd=LOCAL_REPO_PATH)

    # Discard tracked file changes
    run_cmd(["git", "reset", "--hard", "HEAD"], cwd=LOCAL_REPO_PATH)

    # Remove untracked files/folders
    run_cmd(["git", "clean", "-fd"], cwd=LOCAL_REPO_PATH)

    logging.info("Repository cleaned successfully.")


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
        # Perform revert without auto commit first (safe check)
        run_cmd(["git", "revert", "--no-commit", commit_sha], cwd=LOCAL_REPO_PATH)

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

    reverted_count = 0

    for commit in ordered:
        sha = commit["sha"]

        try:
            revert_commit(sha)
            reverted_count += 1

        except Exception as e:
            logging.error(f"Rollback stopped at {sha}")
            raise Exception(f"Rollback failed at {sha}")
    return reverted_count


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
#------------------------------
def push_branch(branch_name: str):
    """
    Push rollback branch to remote
    """

    logging.info(f"Pushing branch: {branch_name}")

    # DEBUG
    remote_url = run_cmd(
        ["git", "remote", "get-url", "origin"],
        cwd=LOCAL_REPO_PATH
    )

    logging.info(f"Origin URL = {remote_url}")

    run_cmd([
        "git",
        "push",
        "-u",
        "origin",
        branch_name
    ], cwd=LOCAL_REPO_PATH)