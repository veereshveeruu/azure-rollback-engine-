

def generate_branch_name(release_id: str, work_item_id: str) -> str:
    return f"rollback/release-{release_id}-story-{work_item_id}"