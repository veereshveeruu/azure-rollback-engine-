from utils.branch_utils import generate_branch_name

def test_generate_branch_name():
    branch = generate_branch_name("LOCAL", "20")
    assert branch == "rollback/release-LOCAL-story-20"