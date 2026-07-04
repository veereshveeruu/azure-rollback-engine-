from sha_validator import generate_repo_sha256

repo_path = "./repo"   # Use the same repository path your rollback engine uses

current_sha = generate_repo_sha256(repo_path)

print("Current SHA:", current_sha)