import os
import getpass
import platform


def get_execution_context():

    github_actor = os.getenv("GITHUB_ACTOR")

    if github_actor:
        return {
            "executed_by": github_actor,
            "host_machine": "GitHub Runner",
            "execution_mode": "GITHUB_ACTIONS"
        }

    return {
        "executed_by": getpass.getuser(),
        "host_machine": platform.node(),
        "execution_mode": "LOCAL_EXECUTION"
    }