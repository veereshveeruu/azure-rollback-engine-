def log_rollback_summary(
    logger,
    work_item_id,
    work_item_url,
    pr_number,
    commits,
    branch_name,
    rollback_pr_url,
    rollback_status,
    merge_status
):
    logger.info("=" * 68)
    logger.info("ROLLBACK SUMMARY")
    logger.info("=" * 68)

    logger.info("Work Item")
    logger.info(f"├── ID       : {work_item_id}")
    logger.info(f"├── URL      : {work_item_url}")
    logger.info(f"├── PR       : {pr_number}")
    logger.info(f"├── Branch   : {branch_name}")
    logger.info("├── Commits")

    total = len(commits)

    for index, commit in enumerate(commits):
        sha = commit["sha"][:7]

        if index == total - 1:
            logger.info(f"│   └── {sha}")
        else:
            logger.info(f"│   ├── {sha}")

    logger.info(f"├── Review PR        : {rollback_pr_url}")
    logger.info(f"├── Rollback Status  : {rollback_status}")
    logger.info(f"└── Merge Status     : {merge_status}")
    logger.info("=" * 68)