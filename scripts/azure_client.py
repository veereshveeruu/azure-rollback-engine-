import os
import base64
import logging
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# -----------------------------
# CONFIG
# -----------------------------
AZURE_ORG = os.getenv("AZURE_ORG")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")
AZURE_PAT = os.getenv("AZURE_PAT")

BASE_URL = f"{AZURE_ORG}/{AZURE_PROJECT}/_apis/wit/workitems"

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
def get_work_item(work_item_id: str):
    """
    Fetch full work item including relations
    """
    url = f"{BASE_URL}/{work_item_id}?$expand=relations&api-version={API_VERSION}"
    req = Request(url, headers=get_headers(), method="GET")

    try:
        with urlopen(req) as response:
            body = response.read().decode()
            return json.loads(body)
    except HTTPError as e:
        error_text = e.read().decode()
        logging.error(f"Failed to fetch work item {work_item_id}: {error_text}")
        raise Exception(f"Azure API error: {error_text}") from e
    except URLError as e:
        logging.error(f"Failed to fetch work item {work_item_id}: {e}")
        raise Exception(f"Azure API network error: {e}") from e


# -----------------------------
# STEP 2: EXTRACT PR LINKS
# -----------------------------
def extract_pr_links(work_item_json):
    """
    Extract GitHub Pull Requests from Azure Boards relations
    """

    relations = work_item_json.get("relations", [])

    pr_links = []

    for rel in relations:
        url = rel.get("url", "")

        if "GitHub/PullRequest" in url:
            pr_links.append(url)

    return pr_links


# -----------------------------
# STEP 3: EXTRACT PR NUMBER
# -----------------------------
def extract_pr_number(pr_url: str):
    """
    Extract PR number from Azure GitHub artifact link

    Example:
    vstfs:///GitHub/PullRequest/xxxx%2f2
    -> 2
    """

    return pr_url.split("%2f")[-1]

# -----------------------------
# STEP 4: MAIN FUNCTION
# -----------------------------
# -----------------------------
# STEP 4: MAIN FUNCTION
# -----------------------------
def get_pr_from_work_item(work_item_id: str):
    """
    END-TO-END:
    Azure Work Item → GitHub PR number(s)
    """

    work_item = get_work_item(work_item_id)

    print("===== RELATIONS =====")
    print(json.dumps(work_item.get("relations", []), indent=2))
    print("=====================")

    pr_links = extract_pr_links(work_item)

    if not pr_links:
        logging.warning(f"No PR linked to Work Item: {work_item_id}")
        return []

    pr_numbers = []

    for link in pr_links:
     pr_numbers.append({
        "url": link,
        "pr_number": extract_pr_number(link)
    })

    # Latest PR first
    pr_numbers.sort(
    key=lambda x: int(x["pr_number"]),
    reverse=True
)

    logging.info(f"PRs Found: {pr_numbers}")
    return pr_numbers