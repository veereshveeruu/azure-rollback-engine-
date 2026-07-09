import os
import base64
import logging
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from github_client import search_pr_by_work_item

# -----------------------------
# CONFIG
# -----------------------------
AZURE_ORG = os.getenv("AZURE_ORG")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")
AZURE_PAT = os.getenv("AZURE_PAT")


BASE_URL = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_apis/wit/workitems"

API_VERSION = "7.0"

# -----------------------------
# AUTH HEADERS
# -----------------------------
def get_headers():
    """
    Azure DevOps uses Basic Auth with PAT
    """
    token = base64.b64encode(f":{AZURE_PAT}".encode()).decode()

    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }


# -----------------------------
# STEP 1: FETCH WORK ITEM
# -----------------------------
def get_work_item(work_item_id):

    url = (
    f"{BASE_URL}/{work_item_id}"
    f"?$expand=relations"
    f"&api-version={API_VERSION}"
)

    try:
        req = Request(
            url,
            headers=get_headers()
        )

        response = urlopen(req)

        body = response.read().decode("utf-8")

        # Validate JSON response
        try:
            return json.loads(body)

        except json.JSONDecodeError:
            logging.error(
                "Azure returned invalid JSON response"
            )

            logging.error(
                f"Response Body:\n{body[:500]}"
            )

            raise Exception(
                "Azure API returned invalid response. "
                "Check PAT, organization, project configuration."
            )


    except HTTPError as e:

        error_body = e.read().decode("utf-8")

        logging.error(
            f"Azure API HTTP Error: {e.code}"
        )

        logging.error(
            f"Response:\n{error_body[:500]}"
        )

        raise Exception(
            f"Azure API failed with status {e.code}"
        )


    except URLError as e:

        logging.error(
            f"Azure connection error: {str(e)}"
        )

        raise Exception(
            "Unable to connect to Azure DevOps"
        )


# -----------------------------
# STEP 2: EXTRACT PR LINKS
# -----------------------------
def extract_pr_links(work_item_json):

    relations = work_item_json.get("relations", [])

    pr_links = []

    for rel in relations:
        if (
            rel.get("rel") == "ArtifactLink"
            and rel.get("attributes", {}).get("name") == "GitHub Pull Request"
        ):
            pr_links.append(rel["url"])

    return pr_links
# -----------------------------
# STEP 3: EXTRACT PR NUMBER
# -----------------------------



def extract_pr_number(pr_link):
    """
    Extract PR number from Azure DevOps GitHub PR artifact link.
    """

    decoded = unquote(pr_link)

    return decoded.rstrip("/").split("/")[-1]


def set_release_id_env(work_item):
    """
    Extract release id from work item.
    Used for branch naming.
    """

    fields = work_item.get("fields", {})

    release_id = (
        fields.get("Custom.ReleaseId")
        or fields.get("ReleaseId")
        or os.getenv("RELEASE_ID", "LOCAL")
    )

    os.environ["RELEASE_ID"] = str(release_id)

    return release_id
# -----------------------------
# STEP 4: MAIN FUNCTION
def get_pr_from_work_item(work_item_id: str):

    work_item = get_work_item(work_item_id)

    set_release_id_env(work_item)

    pr_links = extract_pr_links(work_item)

    if not pr_links:

        logging.warning(
            f"No Azure PR relation found for Work Item: {work_item_id}"
        )

        pr_number = search_pr_by_work_item(work_item_id)

        if pr_number:
            logging.info(
                f"GitHub fallback found PR #{pr_number}"
            )

            return [
                {
                    "url": f"github-pr-{pr_number}",
                    "pr_number": pr_number
                }
            ]

        return []

    pr_numbers = []

    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")

    for link in pr_links:
        pr_number = extract_pr_number(link)

        pr_numbers.append(
            {
                "url": (
                    f"https://github.com/"
                    f"{github_owner}/"
                    f"{github_repo}/pull/{pr_number}"
                ),
                "pr_number": pr_number
            }
        )

    pr_numbers.sort(
        key=lambda x: int(x["pr_number"]),
        reverse=True
    )

    return pr_numbers