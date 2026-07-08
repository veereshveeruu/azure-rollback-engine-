import os
from unittest.mock import patch

# Required before importing the module
os.environ["GIT_REPO_URL"] = "https://github.com/test/repo.git"
os.environ["LOCAL_REPO_PATH"] = "/tmp/repo"
os.environ["GITHUB_TOKEN"] = "dummy-token"

from scripts.git_operations import (
    clone_repo,
    branch_exists_local,
    branch_exists_remote,
    commit_revert_changes,
    create_rollback_branch,
    push_branch,
    revert_commits,
)

@patch("scripts.git_operations.run_cmd")
@patch("scripts.git_operations.os.path.exists")
def test_clone_repo(mock_exists, mock_run):

    mock_exists.return_value = False

    clone_repo()

    mock_run.assert_called_once()

@patch("scripts.git_operations.run_cmd")
def test_branch_exists_local(mock_run):

    mock_run.return_value = "rollback/test"

    assert branch_exists_local("rollback/test") is True

@patch("scripts.git_operations.run_cmd")
def test_branch_exists_remote(mock_run):

    mock_run.return_value = "refs/heads/rollback/test"

    assert branch_exists_remote("rollback/test") is True

@patch("scripts.git_operations.run_cmd")
def test_create_rollback_branch(mock_run):

    create_rollback_branch("rollback/test")

    mock_run.assert_called_once()

@patch("scripts.git_operations.run_cmd")
def test_push_branch(mock_run):

    push_branch("rollback/test")

    mock_run.assert_called_once()

@patch("scripts.git_operations.revert_commit")
def test_revert_commits(mock_revert):

    commits = [
        {
            "sha": "111",
            "date": "2026-07-01T10:00:00Z"
        },
        {
            "sha": "222",
            "date": "2026-07-02T10:00:00Z"
        },
        {
            "sha": "333",
            "date": "2026-07-03T10:00:00Z"
        }
    ]

    count = revert_commits(commits)

    assert count == 3

    expected = ["333", "222", "111"]

    actual = [
        call.args[0]
        for call in mock_revert.call_args_list
    ]

    assert actual == expected

@patch("scripts.git_operations.run_cmd")
def test_commit_revert_changes_no_changes(mock_run):

    mock_run.return_value = ""

    commit_revert_changes("Rollback")

    mock_run.assert_called_once()