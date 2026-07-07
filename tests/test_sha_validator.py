
import os
import tempfile

from scripts.sha_validator import (
    hash_file,
    collect_files,
    build_file_hash_map,
    generate_repo_sha256,
    save_sha_snapshot,
    load_sha_snapshot,
)

def test_hash_file():
    """Verify SHA256 hash is generated for a file."""

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"Hello World")
        file_path = f.name

    sha = hash_file(file_path)

    assert len(sha) == 64

    os.remove(file_path)


def test_collect_files():
    """Verify files are collected correctly."""

    with tempfile.TemporaryDirectory() as repo:

        open(os.path.join(repo, "a.txt"), "w").write("A")
        open(os.path.join(repo, "b.txt"), "w").write("B")

        files = collect_files(repo)

        assert len(files) == 2


def test_build_file_hash_map():
    """Verify file hash map is created."""

    with tempfile.TemporaryDirectory() as repo:

        open(os.path.join(repo, "sample.txt"), "w").write("Rollback Engine")

        file_map = build_file_hash_map(repo)

        assert "sample.txt" in file_map
        assert len(file_map["sample.txt"]) == 64


def test_generate_repo_sha256():
    """Verify repository SHA is generated."""

    with tempfile.TemporaryDirectory() as repo:

        open(os.path.join(repo, "one.txt"), "w").write("ABC")
        open(os.path.join(repo, "two.txt"), "w").write("XYZ")

        sha = generate_repo_sha256(repo)

        assert len(sha) == 64


def test_save_and_load_snapshot():
    """Verify snapshot can be saved and loaded."""

    with tempfile.TemporaryDirectory() as repo:

        snapshot = os.path.join(repo, "sha.txt")

        save_sha_snapshot(snapshot, "123456")

        sha = load_sha_snapshot(snapshot)

        assert sha == "123456"


def test_load_snapshot_file_not_found():
    """Verify None is returned when snapshot does not exist."""

    sha = load_sha_snapshot("non_existing_sha.txt")

    assert sha is None