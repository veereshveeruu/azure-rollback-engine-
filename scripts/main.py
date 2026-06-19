import os
import logging
from datetime import datetime
from logger import setup_logger
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.env_loader import load_env

load_env()

logger = setup_logger("rollback-engine")

# Import your modules
from azure_client import get_pr_from_work_item
from github_client import get_pr_commits
from git_operations import (
    clone_repo,
    create_rollback_branch,
    revert_commits,
    commit_revert_changes,
    push_branch,
    ensure_clean_state,
    LOCAL_REPO_PATH
)
from sha_validator import (
    generate_repo_sha256,
    save_sha_snapshot,
    compare_sha
)

# -----------------------------
# LOGGING CONFIG
# -----------------------------
LOG_FILE = f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def run_pipeline(work_item_id: str):
    try:
        logging.info("========== PIPELINE STARTED ==========")
        logging.info(f"Work Item ID: {work_item_id}")

        # -------------------------
        # STEP 1: Azure → PR
        # -------------------------
        logging.info("Fetching PR from Azure...")

        pr_data = get_pr_from_work_item(work_item_id)

        if not pr_data:
            raise Exception("No PR linked to Azure Work Item")

        pr_number = pr_data[0]["pr_number"]

        logging.info(f"PR Found: {pr_number}")

        # -------------------------
        # STEP 2: PR → Commits
        # -------------------------
        logging.info("Fetching commits from GitHub...")

        commits = get_pr_commits(pr_number)

        if not commits:
            raise Exception("No commits found in PR")

        logging.info(f"Total commits: {len(commits)}")

        # -------------------------
        # STEP 3: Clone Repo
        # -------------------------
        logging.info("Cloning repository...")

        logging.info(f"GIT_REPO_URL = {os.getenv('GIT_REPO_URL')}")
        logging.info(f"LOCAL_REPO_PATH = {LOCAL_REPO_PATH}")

        clone_repo()

        # -------------------------
        # STEP 4: Clean Check
        # -------------------------
        ensure_clean_state()

        # -------------------------
        # STEP 5: Create Rollback Branch
        # -------------------------
        branch_name = f"rollback/story-{work_item_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        create_rollback_branch(branch_name)

        logging.info(f"Rollback branch created: {branch_name}")

        # -------------------------
        # STEP 6: SHA BEFORE
        # -------------------------
        logging.info("Generating SHA BEFORE snapshot...")

        sha_before = generate_repo_sha256(LOCAL_REPO_PATH)

        save_sha_snapshot("sha256-before.txt", sha_before)

        logging.info(f"SHA BEFORE: {sha_before}")

        # -------------------------
        # STEP 7: REVERT COMMITS
        # -------------------------
        logging.info("Starting commit revert process...")

        revert_commits(commits)

        # -------------------------
        # STEP 8: COMMIT CHANGES
        # -------------------------
        commit_revert_changes(
            message=f"Rollback for WorkItem {work_item_id}"
        )

        # -------------------------
        # STEP 9: SHA AFTER
        # -------------------------
        logging.info("Generating SHA AFTER snapshot...")

        sha_after = generate_repo_sha256(LOCAL_REPO_PATH)

        save_sha_snapshot("sha256-after.txt", sha_after)

        logging.info(f"SHA AFTER: {sha_after}")

        # -------------------------
        # STEP 10: VALIDATION
        # -------------------------
        logging.info("Validating rollback integrity...")

        if compare_sha(sha_before, sha_after):
            logging.info("ROLLBACK SUCCESS - SHA MATCHED")
            status = "SUCCESS"
        else:
            logging.error("ROLLBACK FAILED - SHA MISMATCH")
            status = "FAILED"

        # -------------------------
        # STEP 11: PUSH BRANCH
        # -------------------------
        logging.info("Pushing rollback branch...")

        push_branch(branch_name)

        logging.info("========== PIPELINE COMPLETED ==========")

        return {
            "status": status,
            "work_item": work_item_id,
            "pr": pr_number,
            "branch": branch_name,
            "sha_before": sha_before,
            "sha_after": sha_after,
            "log_file": LOG_FILE
        }

    except Exception as e:
        logging.exception("PIPELINE FAILED")

        return {
            "status": "FAILED",
            "error": str(e),
            "log_file": LOG_FILE
        }


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":

    work_item_id = os.getenv("WORK_ITEM_ID")

    if not work_item_id:
        print("ERROR: WORK_ITEM_ID not provided")
        exit(1)

    result = run_pipeline(work_item_id)

    print("\n========== RESULT ==========")
    print(result)