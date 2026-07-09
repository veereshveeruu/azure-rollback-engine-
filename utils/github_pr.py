import os
import json
import urllib.request
import urllib.error
from types import SimpleNamespace



# Try to import requests; if unavailable, provide a minimal fallback using urllib
try:
    import requests  # type: ignore
except Exception:
    def _post(url, headers=None, json=None):
        data = json and bytes(json_module.dumps(json), encoding="utf-8") or None
        req = urllib.request.Request(url, data=data, method="POST")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req) as resp:
                resp_data = resp.read()
                text = resp_data.decode("utf-8")
                status = resp.getcode()
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8") if hasattr(e, 'read') else str(e)
            status = e.code if hasattr(e, 'code') else 0

        class _Resp:
            def __init__(self, status, text):
                self.status_code = status
                self.text = text
            def json(self):
                try:
                    return json_module.loads(self.text)
                except Exception:
                    return {}

        return _Resp(status, text)

    # avoid shadowing json module name
    json_module = json
    requests = SimpleNamespace(post=_post)


def create_pull_request(
    branch_name,
    base_branch,
    title,
    body
):
    github_token = os.getenv("GITHUB_TOKEN")
    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")


    url = f"https://api.github.com/repos/{github_owner}/{github_repo}/pulls"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
    "title": title,
    "head": branch_name,
    "base": base_branch,
    "body": body
}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 201:
        raise Exception(
            f"Failed to create Pull Request: {response.text}"
        )

    return response.json()