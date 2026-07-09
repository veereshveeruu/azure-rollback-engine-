import logging
import os
import subprocess
from typing import List, Dict


# -----------------------------
# CONFIGURATION
# -----------------------------

GIT_REPO_URL = os.getenv("GIT_REPO_URL")
LOCAL_REPO_PATH = os.getenv("LOCAL_REPO_PATH", "/tmp/repo")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


if not GIT_REPO_URL:
    raise Exception("GIT_REPO_URL is missing")

if not LOCAL_REPO_PATH:
    raise Exception("LOCAL_REPO_PATH is missing")


if GITHUB_TOKEN:
    GIT_REPO_URL = GIT_REPO_URL.replace(
        "https://",
        f"https://x-access-token:{GITHUB_TOKEN}@"
    )


# -----------------------------
# COMMAND EXECUTION
# -----------------------------

def run_cmd(cmd: List[str], cwd: str = None) -> str:
    """Execute shell command safely."""

    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True
    )

    if result.returncode != 0:

        # Ignore abort failures when nothing exists
        if (
            cmd[:3] in [
                ["git", "revert", "--abort"],
                ["git", "merge", "--abort"]
            ]
        ):
            return result.stdout

        logging.error(
            f"Command failed: {' '.join(cmd)}"
        )

        logging.error(result.stderr)

        raise Exception(
            f"Command failed:\n{' '.join(cmd)}\n"
            f"{result.stderr}"
        )

    return result.stdout


# -----------------------------
# REPOSITORY MANAGEMENT
# -----------------------------

def clone_repo():
    """Clone repository if not already available."""

    if os.path.exists(LOCAL_REPO_PATH):
        return

    run_cmd(
        [
            "git",
            "clone",
            GIT_REPO_URL,
            LOCAL_REPO_PATH
        ]
    )


def configure_remote_auth():
    """Configure GitHub token authentication."""

    if not GITHUB_TOKEN:
        raise Exception("GITHUB_TOKEN missing")

    run_cmd(
        [
            "git",
            "remote",
            "set-url",
            "origin",
            GIT_REPO_URL
        ],
        cwd=LOCAL_REPO_PATH
    )


def configure_git_user():

    run_cmd(
        [
            "git",
            "config",
            "user.email",
            "github-actions@github.com"
        ],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        [
            "git",
            "config",
            "user.name",
            "github-actions[bot]"
        ],
        cwd=LOCAL_REPO_PATH
    )


# -----------------------------
# BRANCH MANAGEMENT
# -----------------------------

def reset_to_branch(branch_name: str):

    run_cmd(
        ["git", "fetch", "origin"],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        [
            "git",
            "checkout",
            f"origin/{branch_name}"
        ],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        [
            "git",
            "checkout",
            "-B",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )


def branch_exists_local(branch_name: str) -> bool:

    result = run_cmd(
        [
            "git",
            "branch",
            "--list",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )

    return bool(result.strip())


def branch_exists_remote(branch_name: str) -> bool:

    result = run_cmd(
        [
            "git",
            "ls-remote",
            "--heads",
            "origin",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )

    return bool(result.strip())


def delete_local_branch(branch_name: str):

    run_cmd(
        [
            "git",
            "branch",
            "-D",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )


def delete_remote_branch(branch_name: str):

    run_cmd(
        [
            "git",
            "push",
            "origin",
            "--delete",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )


def ensure_clean_rollback_branch(branch_name: str):

    run_cmd(
        ["git", "checkout", "main"],
        cwd=LOCAL_REPO_PATH
    )

    if branch_exists_local(branch_name):
        delete_local_branch(branch_name)

    if branch_exists_remote(branch_name):
        delete_remote_branch(branch_name)


def create_rollback_branch(branch_name: str):

    logging.info(
        f"Creating rollback branch: {branch_name}"
    )

    run_cmd(
        [
            "git",
            "checkout",
            "-b",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )


# -----------------------------
# CLEAN WORKSPACE
# -----------------------------

def ensure_clean_state():

    run_cmd(
        ["git", "revert", "--abort"],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        ["git", "merge", "--abort"],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        ["git", "reset", "--hard", "HEAD"],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        ["git", "clean", "-fd"],
        cwd=LOCAL_REPO_PATH
    )


# -----------------------------
# ROLLBACK ENGINE
# -----------------------------

def revert_commit(commit_sha: str):

    run_cmd(
        [
            "git",
            "revert",
            "--no-commit",
            commit_sha
        ],
        cwd=LOCAL_REPO_PATH
    )

    status = run_cmd(
        [
            "git",
            "status",
            "--porcelain"
        ],
        cwd=LOCAL_REPO_PATH
    )

    if any(
        conflict in status
        for conflict in ["UU", "AA", "DD"]
    ):
        run_cmd(
            [
                "git",
                "revert",
                "--abort"
            ],
            cwd=LOCAL_REPO_PATH
        )

        raise Exception(
            f"Merge conflict detected: {commit_sha}"
        )


def revert_commits(commits: List[Dict]):

    commits = sorted(
        commits,
        key=lambda x: x["date"],
        reverse=True
    )

    count = 0

    for commit in commits:

        revert_commit(commit["sha"])
        count += 1

    return count


def get_commit_date(commit_sha: str):

    return run_cmd(
        [
            "git",
            "show",
            "-s",
            "--format=%cI",
            commit_sha
        ],
        cwd=LOCAL_REPO_PATH
    ).strip()


def revert_commit_ids(commit_ids: List[str]):

    commits = [
        {
            "sha": sha,
            "date": get_commit_date(sha)
        }
        for sha in commit_ids
    ]

    return revert_commits(commits)

def rollback_by_commit_ids(
    source_branch: str,
    rollback_branch: str,
    commit_ids: List[str]
):
    reset_to_branch(source_branch)
    ensure_clean_rollback_branch(rollback_branch)
    create_rollback_branch(rollback_branch)

    reverted = revert_commit_ids(commit_ids)

    commit_revert_changes(
        "Rollback using commit IDs"
    )

    push_branch(rollback_branch)

    return reverted

# -------------------------------
# STEP 9: COMMIT CHANGES (WITH CI SKIP)
# -------------------------------
def commit_revert_changes(message: str):

    status = run_cmd(
        [
            "git",
            "status",
            "--porcelain"
        ],
        cwd=LOCAL_REPO_PATH
    )

    if not status.strip():
        logging.warning(
            "No changes available to commit"
        )
        return

    run_cmd(
        ["git", "add", "-A"],
        cwd=LOCAL_REPO_PATH
    )

    run_cmd(
        [
            "git",
            "commit",
            "-m",
            f"{message} [skip ci]"
        ],
        cwd=LOCAL_REPO_PATH
    )


def push_branch(branch_name: str):

    logging.info(
        f"Pushing branch: {branch_name}"
    )

    run_cmd(
        [
            "git",
            "push",
            "-u",
            "origin",
            branch_name
        ],
        cwd=LOCAL_REPO_PATH
    )