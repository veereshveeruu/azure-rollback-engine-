import pytest

from utils.branch_utils import generate_branch_name


def test_generate_branch_name():
    """
    Verify rollback branch name is generated correctly.
    """
    branch = generate_branch_name("LOCAL", "20")

    assert branch == "rollback/release-LOCAL-story-20"


def test_generate_branch_name_numeric_release():
    """
    Verify numeric release IDs are handled correctly.
    """
    branch = generate_branch_name("101", "45")

    assert branch == "rollback/release-101-story-45"


def test_generate_branch_name_empty_values():
    """
    Verify function still returns a valid formatted string.
    """
    branch = generate_branch_name("", "")

    assert branch == "rollback/release--story-"