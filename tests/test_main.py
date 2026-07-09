import os
from pdb import main
from unittest.mock import patch, MagicMock
import scripts.main as main

# Required environment variables
os.environ["WORK_ITEM_IDS"] = "20"
os.environ["GIT_REPO_URL"] = "https://github.com/test/repo.git"
os.environ["LOCAL_REPO_PATH"] = "/tmp/repo"
os.environ["GITHUB_TOKEN"] = "dummy-token"



@patch("scripts.main.run_cmd")
@patch("scripts.main.create_pull_request")
@patch("scripts.main.push_branch")
@patch("scripts.main.compare_sha")
@patch("scripts.main.generate_repo_sha256")
@patch("scripts.main.commit_revert_changes")
@patch("scripts.main.revert_commits")
@patch("scripts.main.ensure_clean_state")
@patch("scripts.main.reset_to_branch")
@patch("scripts.main.configure_remote_auth")
@patch("scripts.main.configure_git_user")
@patch("scripts.main.clone_repo")
@patch("scripts.main.create_rollback_branch")
@patch("scripts.main.ensure_clean_rollback_branch")
@patch("scripts.main.get_pr_commits")
@patch("scripts.main.get_pr_from_work_item")

def test_run_pipeline_success(
    mock_get_pr,
    mock_get_commits,
    mock_clean_branch,
    mock_create_branch,
    mock_clone,
    mock_git_user,
    mock_remote_auth,
    mock_reset,
    mock_clean_state,
    mock_revert,
    mock_commit,
    mock_sha,
    mock_compare,
    mock_push,
    mock_create_pr,
    mock_run_cmd
):

    # Azure Work Item -> PR
    mock_get_pr.return_value = [
        {
            "url": "vstfs:///GitHub/PullRequest/test%2f35",
            "pr_number": "35"
        }
    ]


    # PR -> Commits
    mock_get_commits.return_value = [
        {
            "sha": "abc123",
            "date": "2026-07-01"
        }
    ]


    # SHA before and after
    mock_sha.side_effect = [
        "before_sha_value",
        "after_sha_value"
    ]


    # GitHub PR creation
    mock_create_pr.return_value = {
        "number": 50,
        "html_url": "https://github.com/test/pull/50"
    }


    result = main.run_pipeline("20")


    assert result["status"] == "SUCCESS"
    assert result["work_item"] == "20"
    assert result["feature_pr"] == "35"
    assert result["rollback_pr"] == 50
@patch("scripts.main.get_pr_from_work_item")

def test_run_pipeline_failure(mock_get_pr):

    mock_get_pr.return_value = []

    result = main.run_pipeline("20")

    assert result["status"] == "FAILED"
    assert result["work_item"] == "20"

@patch("scripts.main.run_pipeline")
@patch("scripts.main.AuditReport")
def test_multiple_work_items(mock_audit, mock_run_pipeline):

    work_item_ids = ["20", "21"]

    mock_run_pipeline.side_effect = [
        {"status": "SUCCESS", "work_item": work_item_ids[0]},
        {"status": "SUCCESS", "work_item": work_item_ids[1]},
    ]

    audit = MagicMock()
    mock_audit.return_value = audit

    results = []

    for work_item_id in work_item_ids:
        result = main.run_pipeline(work_item_id)
        audit.add_result(result)
        results.append(result)

    assert mock_run_pipeline.call_count == 2
    assert audit.add_result.call_count == 2

    assert results[0]["work_item"] == "20"
    assert results[1]["work_item"] == "21"

    assert results[0]["status"] == "SUCCESS"
    assert results[1]["status"] == "SUCCESS"


@patch("scripts.main.run_pipeline")
@patch("scripts.main.AuditReport")
def test_multiple_work_items_with_failure(
    mock_audit,
    mock_run_pipeline
):

    work_item_ids = ["20", "21"]

    mock_run_pipeline.side_effect = [
        {"status": "SUCCESS", "work_item": work_item_ids[0]},
        {"status": "FAILED", "work_item": work_item_ids[1]},
    ]

    audit = MagicMock()
    mock_audit.return_value = audit

    results = []

    for work_item_id in work_item_ids:
        result = main.run_pipeline(work_item_id)
        audit.add_result(result)
        results.append(result)

    assert len(results) == 2

    assert results[0]["status"] == "SUCCESS"
    assert results[1]["status"] == "FAILED"

    assert audit.add_result.call_count == 2

from unittest.mock import patch


@patch("scripts.main.get_pr_from_work_item")
def test_multiple_prs_for_single_work_item(mock_get_pr):

    # One Work Item linked with multiple PRs
    mock_get_pr.return_value = [
        {
            "url": "https://github.com/test/repo/pull/35",
            "pr_number": "35"
        },
        {
            "url": "https://github.com/test/repo/pull/40",
            "pr_number": "40"
        },
        {
            "url": "https://github.com/test/repo/pull/45",
            "pr_number": "45"
        }
    ]


    pr_data = mock_get_pr("20")

 
    # Verify multiple PRs are returned
    assert len(pr_data) == 3

    assert pr_data[0]["pr_number"] == "35"
    assert pr_data[1]["pr_number"] == "40"
    assert pr_data[2]["pr_number"] == "45"

    assert mock_get_pr.call_count == 1