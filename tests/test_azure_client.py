import os
from unittest.mock import patch

from scripts.azure_client import (
    get_headers,
    extract_pr_links,
    extract_pr_number,
    set_release_id_env,
    get_pr_from_work_item,
)


def test_get_headers():
    headers = get_headers()

    assert "Authorization" in headers
    assert headers["Content-Type"] == "application/json"


def test_extract_pr_links():

    work_item = {
        "relations": [
            {
                "rel": "ArtifactLink",
                "url": "vstfs:///GitHub/PullRequest/abc%2f35",
                "attributes": {
                    "name": "GitHub Pull Request"
                }
            }
        ]
    }

    links = extract_pr_links(work_item)

    assert len(links) == 1
    assert links[0].endswith("%2f35")


def test_extract_pr_number():

    url = "vstfs:///GitHub/PullRequest/abc%2f48"

    assert extract_pr_number(url) == "48"


def test_set_release_id_env():

    work_item = {
        "fields": {
            "Custom.ReleaseId": "LOCAL"
        }
    }

    release = set_release_id_env(work_item)

    assert release == "LOCAL"
    assert os.environ["RELEASE_ID"] == "LOCAL"


@patch("scripts.azure_client.get_work_item")
def test_get_pr_from_work_item(mock_get_work_item):

    mock_get_work_item.return_value = {
        "fields": {
            "Custom.ReleaseId": "LOCAL"
        },
        "relations": [
            {
                "rel": "ArtifactLink",
                "url": "vstfs:///GitHub/PullRequest/abc%2f35",
                "attributes": {
                    "name": "GitHub Pull Request"
                }
            }
        ]
    }

    result = get_pr_from_work_item("20")

    assert len(result) == 1
    assert result[0]["pr_number"] == "35"