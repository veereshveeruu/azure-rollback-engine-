import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

sys.path.insert(0, project_root)
sys.path.insert(0, script_dir)

import logging
import json
from datetime import datetime

from logger import setup_logger
from utils.audit_report import AuditReport
from utils.env_loader import load_env
from utils.branch_utils import generate_branch_name
from utils.github_pr import create_pull_request

load_env()

logger = setup_logger("rollback-engine")

from azure_client import get_pr_from_work_item
from github_client import GITHUB_OWNER, get_pr_commits
import github_client
from utils.release_utils import get_release_id
from utils.runtime_utils import get_current_user
from utils.log_summary import log_rollback_summary

from git_operations import (
    clone_repo,
    configure_git_user,
    create_rollback_branch,
    configure_remote_auth,
    ensure_clean_state,
    reset_to_main,
    ensure_clean_rollback_branch,
    revert_commits,
    commit_revert_changes,
    push_branch,
    LOCAL_REPO_PATH,
    run_cmd
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
        logging.info(f"Executed By : {get_current_user()}")
        logging.info(f"Work Item ID: {work_item_id}")

        # STEP 1: Azure → PR
        pr_data = get_pr_from_work_item(work_item_id)

        if not pr_data:
            raise Exception("No PR linked to Azure Work Item")

        work_item_url = pr_data[0]["url"]
        pr_number = pr_data[0]["pr_number"]

        # STEP 2: PR → Commits
        commits = get_pr_commits(pr_number)

        if not commits:
            raise Exception("No commits found in PR")

        logging.info(f"Total commits: {len(commits)}")
        
        logging.info("========== COMMITS FOUND ==========")

        for commit in commits:
            logging.info(commit)

        logging.info("===================================")

        # STEP 3: Clone Repo
        clone_repo()
        configure_git_user()
        configure_remote_auth()
        reset_to_main()
        ensure_clean_state()

        # STEP 4: Create Rollback Branch
        release_id = get_release_id()
        branch_name = generate_branch_name(
            release_id,
            work_item_id
        )
        ensure_clean_rollback_branch(branch_name)
        create_rollback_branch(branch_name)
        logging.info(f"DEBUG LOCAL_REPO_PATH = {LOCAL_REPO_PATH}")
        logging.info(f"DEBUG repo exists = {os.path.exists(LOCAL_REPO_PATH)}")

        # STEP 5: SHA BEFORE
        sha_before = generate_repo_sha256(str(LOCAL_REPO_PATH))
        save_sha_snapshot("sha256-before.txt", sha_before)


        # STEP 5A: Capture files before rollback
        before_files = run_cmd(
            ["git", "diff", "--name-only"],
            cwd=LOCAL_REPO_PATH
        )

        # STEP 6: Revert Commits
        # Use the revert_commits implementation from git_operations
        
        try:
            revert_commits(commits)
        except Exception as e:
            logging.exception(f"Error while reverting commits: {e}")
            status = "FAILED"
            raise

        # STEP 7: COMMIT CHANGES
        try:
            commit_revert_changes(
                f"Rollback for Work Item {work_item_id}"
            )
        except Exception as e:
            logging.exception(f"Error committing revert changes: {e}")
            status = "FAILED"
            raise

        # STEP 8: SHA GENERATION
        sha_after = generate_repo_sha256(str(LOCAL_REPO_PATH))
        save_sha_snapshot("sha256-after.txt", sha_after)

        logging.info(f"SHA AFTER: {sha_after}")
        compare_sha(sha_before, sha_after)
        logging.info("Rollback completed successfully.")
        logging.info("SHA snapshots captured for audit purposes.")
        status = "SUCCESS"

        # STEP 11: PUSH BRANCH
        push_branch(branch_name)
        # STEP 12: CREATE REVIEW PR
        pr_response = create_pull_request(
            branch_name,
            work_item_id
        )

        rollback_pr_number = pr_response["number"]
        rollback_pr_url = pr_response["html_url"]

        logger.info(f"Rollback Pull Request Created: {rollback_pr_url}")

        rollback_status = "SUCCESS"
        merge_status = "PENDING APPROVAL"

        # STEP 13: ROLLBACK SUMMARY
        log_rollback_summary(
            logger=logger,
            work_item_id=work_item_id,
            work_item_url=work_item_url,
            pr_number=rollback_pr_number,
            commits=commits,
            branch_name=branch_name,
            rollback_pr_url=rollback_pr_url,
            rollback_status=rollback_status,
            merge_status=merge_status
        )

        return {
            "status": status,
            "work_item": work_item_id,
            "feature_pr": pr_number,
            "rollback_pr": rollback_pr_number,
            "branch": branch_name,
            "review_pr": rollback_pr_url,
            "sha_before": sha_before,
            "sha_after": sha_after,
            "log_file": LOG_FILE
        }

    except Exception as e:
        logging.exception("========== PIPELINE FAILED ==========")
        logging.error(f"Work Item ID : {work_item_id}")
        logging.error(f"Failure Reason : {str(e)}")
        logging.error("Rollback pipeline terminated.")
        logging.error("=====================================")

        return {
            "status": "FAILED",
            "work_item": work_item_id,
            "error": str(e),
            "log_file": LOG_FILE
        }


# -----------------------------
# ENTRY POINT (MULTI WORK ITEM)
# -----------------------------
if __name__ == "__main__":

    work_item_ids = os.getenv("WORK_ITEM_IDS")

    if not work_item_ids:
        print("ERROR: WORK_ITEM_IDS not provided (example: 8,12,15)")
        exit(1)

    work_item_ids = [item.strip() for item in work_item_ids.split(",")]

    # ✅ INIT AUDIT ONCE
    audit = AuditReport()

    all_results = []

    for work_item_id in work_item_ids:
        logging.info("=" * 80)
        logging.info(f"WORK ITEM ID : {work_item_id}")
        logging.info("STATUS       : STARTED")
        logging.info("=" * 80)

        try:
            result = run_pipeline(work_item_id)

            # ✅ ADD TO AUDIT
            audit.add_result(result)

            all_results.append(result)

        except Exception as e:
            logging.exception(f"Work item {work_item_id} failed")

            failed_result = {
                "work_item": work_item_id,
                "status": "FAILED",
                "error": str(e)
            }

            audit.add_result(failed_result)
            all_results.append(failed_result)

        logging.info("=" * 80)
        logging.info(f"WORK ITEM ID : {work_item_id}")
        logging.info(f"STATUS       : {result['status']}")
        logging.info("=" * 80)

    # -----------------------------
    # FINAL AUDIT REPORT
    # -----------------------------
    audit_file, report = audit.finalize()

    print("\n========== ROLLBACK SUMMARY ==========\n")

    print(f"Status      : {result['status']}")
    print(f"Executed By : {get_current_user()}")
    print(f"Work Item   : {result['work_item']}")

    if result["status"] == "SUCCESS":
     print(f"Feature PR  : {result['feature_pr']}")
     print(f"Rollback PR : {result['rollback_pr']}")
     print(f"Branch      : {result['branch']}")
     print(f"SHA Before  : {result['sha_before'][:12]}...")
     print(f"SHA After   : {result['sha_after'][:12]}...")
    else:
        print(f"Error       : {result['error']}")

    print(f"Log File    : {result['log_file']}")

if result["status"] == "SUCCESS":
    print("\n======================================")
    print("Rollback completed successfully.")
    print("======================================")
else:
    print("\n======================================")
    print("Rollback failed.")
    print("======================================")