import os
import base64

def get_github_headers():
    return {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json"
    }

def get_azure_headers():
    token = base64.b64encode(f":{os.getenv('AZURE_PAT')}".encode()).decode()
    return {
        "Authorization": f"Basic {token}"
    }