import os
from unittest.mock import patch

from scripts.github_client import (
    get_headers,
    sort_commits_by_date,
    validate_pr,
    get_pr_commits,
)


def test_get_headers():
    """Verify GitHub headers are created."""

    os.environ["GITHUB_TOKEN"] = "dummy_token"

    headers = get_headers()

    assert "Authorization" in headers
    assert headers["Accept"] == "application/vnd.github+json"


def test_sort_commits_by_date():
    """Verify commits are sorted oldest -> newest."""

    commits = [
        {"sha": "2", "date": "2026-07-03T10:00:00Z"},
        {"sha": "1", "date": "2026-07-01T10:00:00Z"},
        {"sha": "3", "date": "2026-07-05T10:00:00Z"},
    ]

    ordered = sort_commits_by_date(commits)

    assert ordered[0]["sha"] == "1"
    assert ordered[1]["sha"] == "2"
    assert ordered[2]["sha"] == "3"


@patch("scripts.github_client._http_get")
def test_validate_pr_success(mock_http):

    mock_http.return_value = (200, "{}")

    assert validate_pr("35") is True


@patch("scripts.github_client.validate_pr")
@patch("scripts.github_client.fetch_pr_commits")
def test_get_pr_commits(mock_fetch, mock_validate):

    mock_validate.return_value = True

    mock_fetch.return_value = [
        {
            "sha": "bbb",
            "author": "Veeru",
            "message": "Second",
            "date": "2026-07-02T10:00:00Z",
        },
        {
            "sha": "aaa",
            "author": "Veeru",
            "message": "First",
            "date": "2026-07-01T10:00:00Z",
        },
    ]

    commits = get_pr_commits("35")

    assert len(commits) == 2
    assert commits[0]["sha"] == "aaa"
    assert commits[1]["sha"] == "bbb"


@patch("scripts.github_client.validate_pr")
def test_get_pr_commits_invalid_pr(mock_validate):

    mock_validate.return_value = False

    try:
        get_pr_commits("999")
    except Exception as e:
        assert "not valid" in str(e)