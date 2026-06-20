import os
import logging
from datetime import datetime
from logger import setup_logger
from utils.audit_report import AuditReport
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.env_loader import load_env
load_env()

logger = setup_logger("rollback-engine")

from azure_client import get_pr_from_work_item
from github_client import get_pr_commits
from git_operations import (
    clone_repo,
    configure_git_user,
    create_rollback_branch,
    revert_commits,
    commit_revert_changes,
    push_branch,
    ensure_clean_state,
    LOCAL_REPO_PATH,
    configure_remote_auth,
    reset_to_main,
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
        logging.info(f"Work Item ID: {work_item_id}")

        # STEP 1: Azure → PR
        pr_data = get_pr_from_work_item(work_item_id)

        if not pr_data:
            raise Exception("No PR linked to Azure Work Item")

        pr_number = pr_data[0]["pr_number"]
        logging.info(f"PR Found: {pr_number}")

        # STEP 2: PR → Commits
        commits = get_pr_commits(pr_number)

        if not commits:
            raise Exception("No commits found in PR")

        logging.info(f"Total commits: {len(commits)}")

        # STEP 3: Clone Repo
        clone_repo()
        configure_git_user()
        configure_remote_auth()
        reset_to_main()
        ensure_clean_state()

       # STEP 4: Create Rollback Branch
        branch_name = f"rollback/story-{work_item_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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

       # STEP 6: REVERT COMMIT
        revert_commits(commits)
 
       # STEP 7: COMMIT CHANGES
        commit_revert_changes(
            message=f"Rollback WorkItem {work_item_id}"
        )

        # STEP 8: SHA AFTER
        sha_after = generate_repo_sha256(LOCAL_REPO_PATH)
        save_sha_snapshot("sha256-after.txt", sha_after)

        logging.info(f"SHA AFTER: {sha_after}")

        # STEP 9: VALIDATION
        if compare_sha(sha_before, sha_after):
            logging.info("ROLLBACK SUCCESS - SHA MATCHED")
            status = "SUCCESS"
        else:
            logging.error("ROLLBACK FAILED - SHA MISMATCH")
            status = "FAILED"

        # STEP 10: PUSH BRANCH
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
        logging.info(f"\n\n========== STARTING WORK ITEM {work_item_id} ==========\n")

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

        logging.info(f"========== COMPLETED WORK ITEM {work_item_id} ==========\n")

    # -----------------------------
    # FINAL AUDIT REPORT
    # -----------------------------
    audit_file, report = audit.finalize()

    print("\n========== FINAL RESULTS ==========")
    for r in all_results:
        print(r)

    print("\n========== AUDIT REPORT GENERATED ==========")
    print(f"File: {audit_file}")
    print(json.dumps(report, indent=2))