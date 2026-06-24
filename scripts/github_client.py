import os
import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import List, Dict

# -----------------------------
# CONFIG
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")

BASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

# -----------------------------
# HEADERS
# -----------------------------
def get_headers():
    if not GITHUB_TOKEN:
        raise Exception("Missing GITHUB_TOKEN in environment")

    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }


def _http_get(url: str, headers: Dict[str, str], params: Dict[str, str] = None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, body


# -----------------------------
# STEP 1: VALIDATE PR EXISTS
# -----------------------------
def validate_pr(pr_number: str) -> bool:
    url = f"{BASE_URL}/pulls/{pr_number}"

    status, body = _http_get(url, get_headers())

    if status == 404:
        logging.error(f"PR not found: {pr_number}")
        return False

    if status != 200:
        logging.error(f"GitHub API error: {body}")
        raise Exception(body)

    return True


# -----------------------------
# STEP 2: FETCH COMMITS (PAGINATED SAFE)
# -----------------------------
def fetch_pr_commits(pr_number: str) -> List[Dict]:
    """
    Fetch all commits from a PR with pagination support
    """

    commits = []
    page = 1
    per_page = 100

    while True:
        url = f"{BASE_URL}/pulls/{pr_number}/commits"

        params = {
            "page": page,
            "per_page": per_page
        }

        status, body = _http_get(url, get_headers(), params=params)

        if status != 200:
            logging.error(f"Failed to fetch commits: {body}")
            raise Exception(body)

        data = json.loads(body)

        if not data:
            break

        for c in data:
            commits.append({
                "sha": c["sha"],
                "author": c["commit"]["author"]["name"],
                "message": c["commit"]["message"],
                "date": c["commit"]["author"]["date"]
            })

        page += 1

    return commits


# -----------------------------
# STEP 3: SORT COMMITS (IMPORTANT)
# -----------------------------
def sort_commits_by_date(commits: List[Dict]) -> List[Dict]:
    """
    Ensure correct commit order (oldest → newest)
    """
    return sorted(commits, key=lambda x: x["date"])


# -----------------------------
# STEP 4: MAIN FUNCTION
# -----------------------------
def get_pr_commits(pr_number: str) -> List[Dict]:
    """
    END-TO-END:
    PR → Ordered commits
    """

    logging.info(f"Fetching commits for PR: {pr_number}")

    if not validate_pr(pr_number):
        raise Exception(f"PR {pr_number} not valid or not accessible")

    commits = fetch_pr_commits(pr_number)

    if not commits:
        logging.warning(f"No commits found in PR {pr_number}")
        return []

    ordered = sort_commits_by_date(commits)

    logging.info(f"Total commits found: {len(ordered)}")

    return ordered
