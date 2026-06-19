from dataclasses import dataclass
from utils.helpers import get_env


@dataclass
class Config:

    AZURE_ORG: str = get_env("AZURE_ORG")
    AZURE_PROJECT: str = get_env("AZURE_PROJECT")
    AZURE_PAT: str = get_env("AZURE_PAT")

    GITHUB_TOKEN: str = get_env("GITHUB_TOKEN")
    GITHUB_OWNER: str = get_env("GITHUB_OWNER")
    GITHUB_REPO: str = get_env("GITHUB_REPO")

    GIT_REPO_URL: str = get_env("GIT_REPO_URL")
    LOCAL_REPO_PATH: str = get_env("LOCAL_REPO_PATH", required=False, default="./repo")
    DEFAULT_BRANCH: str = get_env("DEFAULT_BRANCH", required=False, default="main")

    LOG_DIR: str = get_env("LOG_DIR", required=False, default="logs")