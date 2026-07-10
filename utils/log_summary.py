def log_rollback_summary(
    logger,
    work_item_id,
    work_item_url,
    pr_number,
    commits,
    branch_name,
    rollback_pr_url,
    rollback_status,
    merge_status,
    target_branch=None
):
    # Header
    logger.info("=" * 68)
    logger.info("ROLLBACK SUMMARY")
    logger.info("=" * 68)

    # Work item / feature PR info
    logger.info(f"├── ID               : {work_item_id}")
    if work_item_id == "COMMIT_IDS":
        logger.info(f"├── Source Branch    : {target_branch}")
        logger.info(f"├── Branch URL       : {work_item_url}")
    else:
        logger.info(f"├── Feature PR       : {work_item_url.split('/')[-1]}")
        logger.info(f"├── Feature PR URL   : {work_item_url}")

    # Common for both workflows
    logger.info(f"├── Rollback PR      : {pr_number}")
    logger.info(f"├── Branch           : {branch_name}")
    logger.info("├── Commits")

    # Commits list
    if not commits:
        logger.info("│   └── None")
    else:
        total = len(commits)
        for index, commit in enumerate(commits):
            if isinstance(commit, dict):
                sha = commit.get("sha", "")[:7]
            else:
                sha = str(commit)[:7]

            if index == total - 1:
                logger.info(f"│   └── {sha}")
            else:
                logger.info(f"│   ├── {sha}")

    logger.info(f"├── Review PR        : {rollback_pr_url}")
    logger.info(f"├── Rollback Status  : {rollback_status}")
    logger.info(f"└── Merge Status     : {merge_status}")
    logger.info("=" * 68)