import os
from unittest.mock import patch

# Required environment variables
os.environ["WORK_ITEM_IDS"] = "20"
os.environ["GIT_REPO_URL"] = "https://github.com/test/repo.git"
os.environ["LOCAL_REPO_PATH"] = "/tmp/repo"
os.environ["GITHUB_TOKEN"] = "dummy-token"


from scripts.main import run_pipeline

@patch("scripts.main.run_cmd")
@patch("scripts.main.create_pull_request")
@patch("scripts.main.push_branch")
@patch("scripts.main.compare_sha")
@patch("scripts.main.generate_repo_sha256")
@patch("scripts.main.commit_revert_changes")
@patch("scripts.main.revert_commits")
@patch("scripts.main.ensure_clean_state")
@patch("scripts.main.reset_to_main")
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


    result = run_pipeline("20")


    assert result["status"] == "SUCCESS"
    assert result["work_item"] == "20"
    assert result["feature_pr"] == "35"
    assert result["rollback_pr"] == 50
@patch("scripts.main.get_pr_from_work_item")

def test_run_pipeline_failure(mock_get_pr):

    mock_get_pr.return_value = []

    result = run_pipeline("20")

    assert result["status"] == "FAILED"
    assert result["work_item"] == "20"