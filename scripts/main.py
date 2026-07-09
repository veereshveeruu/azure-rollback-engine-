import os
import sys
import logging
from datetime import datetime


# -----------------------------
# PROJECT PATH SETUP
# -----------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

sys.path.insert(0, project_root)
sys.path.insert(0, script_dir)


# -----------------------------
# PROJECT IMPORTS
# -----------------------------
from azure_client import (
    get_work_item,
    get_pr_from_work_item
)

from github_client import get_pr_commits
from logger import setup_logger, get_log_file
from utils.audit_report import AuditReport
from utils.env_loader import load_env
from utils.branch_utils import generate_branch_name
from utils.github_pr import create_pull_request
from utils.runtime_utils import get_current_user
from utils.summary import print_rollback_summary
from utils.log_summary import log_rollback_summary

from git_operations import (
    clone_repo,
    configure_git_user,
    create_rollback_branch,
    configure_remote_auth,
    ensure_clean_state,
    reset_to_branch,
    ensure_clean_rollback_branch,
    revert_commit_ids,
    revert_commits,
    commit_revert_changes,
    push_branch,
    LOCAL_REPO_PATH,
    run_cmd
)

from sha_validator import (
    generate_repo_sha256,
    compare_sha,
    save_sha_snapshot
)


# -----------------------------
# INITIALIZE ENVIRONMENT
# -----------------------------
load_env()

logger = setup_logger("rollback-engine")
# -----------------------------
# LOGGING CONFIG
# -----------------------------


os.makedirs("logs", exist_ok=True)

# -----------------------------
# MAIN PIPELINE
# -----------------------------
def run_pipeline(work_item_id: str):
    work_item_title = "Unknown Title"
    logging.info("=" * 80)
    logging.info(f"New execution started at {datetime.now():%Y-%m-%d %H:%M:%S}")
    logging.info("=" * 80)
    try:
        logging.info("========== PIPELINE STARTED ==========")
        logging.info(f"Executed By : {get_current_user()}")

        work_item = get_work_item(work_item_id)
        work_item_title = work_item.get("fields", {}).get("System.Title", "Unknown Title")

        logging.info(f"Work Item : {work_item_id} - {work_item_title}")


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
        reset_to_branch("main")
        ensure_clean_state()

        # STEP 4: Create Rollback Branch
        branch_name = generate_branch_name(work_item_id)

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
            branch_name=branch_name,
            base_branch="main",
            title=f"Rollback Work Item {work_item_id}",
            body=(
                f"Automated rollback generated for Work Item {work_item_id}.\n\n"
                "Please review and approve before merging."
            )
        )
        rollback_pr_number = pr_response["number"]
        rollback_pr_url = pr_response["html_url"]

        logger.info(f"Rollback Pull Request Created: {rollback_pr_url}")

        rollback_status = "SUCCESS"
        merge_status = "PENDING - Developer Approval"

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
            "work_item_title": work_item_title,
            "feature_pr": pr_number,
            "rollback_pr": rollback_pr_number,
            "branch": branch_name,
            "review_pr": rollback_pr_url,
            "sha_before": sha_before,
            "sha_after": sha_after,
            "log_file": get_log_file()
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
            "work_item_title": work_item_title,
            "error": str(e),
            "log_file": get_log_file()
        }

# -----------------------------
# ENTRY POINT (MULTI WORK ITEM)
# -----------------------------

def rollback_using_commit_ids(target_branch: str, commit_ids: list[str]):
    logging.info("=" * 80)
    logging.info(f"Rollback using commit ids started at {datetime.now():%Y-%m-%d %H:%M:%S}")

    branch_name = f"rollback-{target_branch}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    branch_name = branch_name.replace("/", "-")

    try:
        clone_repo()
        configure_git_user()
        configure_remote_auth()
        reset_to_branch(target_branch)
        ensure_clean_state()

        ensure_clean_rollback_branch(branch_name)
        create_rollback_branch(branch_name)

        sha_before = generate_repo_sha256(str(LOCAL_REPO_PATH))
        save_sha_snapshot("sha256-before.txt", sha_before)

        run_cmd(
            ["git", "diff", "--name-only"],
            cwd=LOCAL_REPO_PATH
        )

        revert_commit_ids(commit_ids)

        commit_revert_changes(
            f"Rollback commits {', '.join(commit_ids)}"
        )

        sha_after = generate_repo_sha256(str(LOCAL_REPO_PATH))
        save_sha_snapshot("sha256-after.txt", sha_after)

        logging.info(f"SHA AFTER: {sha_after}")
        compare_sha(sha_before, sha_after)
        logging.info("Rollback completed successfully.")
        logging.info("SHA snapshots captured for audit purposes.")

        push_branch(branch_name)
        pr_response = create_pull_request(
            branch_name=branch_name,
            base_branch=target_branch,
            title=f"Rollback commits {', '.join(commit_ids)}",
            body=(
                f"Automated rollback generated for commits {', '.join(commit_ids)}.\n\n"
                "Please review and approve before merging."
            )
        )
        rollback_pr_number = pr_response["number"]
        rollback_pr_url = pr_response["html_url"]

        logger.info(f"Rollback Pull Request Created: {rollback_pr_url}")

        rollback_status = "SUCCESS"
        merge_status = "PENDING - Developer Approval"

        log_rollback_summary(
            logger=logger,
            work_item_id="COMMIT_IDS",
            work_item_url=f"target_branch: {target_branch}",
            pr_number=rollback_pr_number,
            commits=commit_ids,
            branch_name=branch_name,
            rollback_pr_url=rollback_pr_url,
            rollback_status=rollback_status,
            merge_status=merge_status
        )
        
        return {
            "status": "SUCCESS",
            "work_item": ",".join(commit_ids),
            "work_item_title": "Rollback using commit IDs",
            "feature_pr": None,
            "rollback_pr": rollback_pr_number,
            "branch": branch_name,
            "review_pr": rollback_pr_url,
            "sha_before": sha_before,
            "sha_after": sha_after,
            "log_file": get_log_file()
        }

    except Exception as e:
        logging.exception("========== COMMIT ID ROLLBACK FAILED ==========")
        logging.error(f"Commit IDs : {commit_ids}")
        logging.error(f"Branch      : {target_branch}")
        logging.error(f"Failure Reason : {str(e)}")
        logging.error("Rollback pipeline terminated.")
        logging.error("=====================================")

        return {
            "status": "FAILED",
            "work_item": ",".join(commit_ids),
            "work_item_title": "Rollback using commit IDs",
            "error": str(e),
            "log_file":get_log_file()
        }


if __name__ == "__main__":
    work_item_ids = os.getenv("WORK_ITEM_IDS")
    commit_ids = os.getenv("COMMIT_IDS")
    target_branch = os.getenv("TARGET_BRANCH")

    if not work_item_ids and not commit_ids:
        print("ERROR: Provide either WORK_ITEM_IDS or COMMIT_IDS")
        exit(1)
    if commit_ids and not target_branch:
        print("ERROR: TARGET_BRANCH is required when using COMMIT_IDS")
        exit(1)

    if work_item_ids:
        work_item_ids = [item.strip() for item in work_item_ids.split(",")]

    if commit_ids:
        commit_ids = [item.strip() for item in commit_ids.split(",")]

    # INIT AUDIT ONCE
    audit = AuditReport()

    all_results = []
    result = None

    if work_item_ids:

        for work_item_id in work_item_ids:
            logging.info("=" * 80)

            try:
                result = run_pipeline(work_item_id)

                audit.add_result(result)
                all_results.append(result)

            except Exception as e:
                failed_result = {
                    "work_item": work_item_id,
                    "status": "FAILED",
                    "error": str(e)
                }

                audit.add_result(failed_result)
                all_results.append(failed_result)

                result = failed_result

    elif commit_ids:

        result = rollback_using_commit_ids(
            target_branch,
            commit_ids
        )

        audit.add_result(result)
        all_results.append(result)


    # -----------------------------
    # FINAL AUDIT REPORT
    # -----------------------------
    audit_file, report = audit.finalize()

    print_rollback_summary(
     result=result,
     log_file=get_log_file()
)