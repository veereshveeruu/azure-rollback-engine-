from utils.runtime_utils import get_current_user


def print_rollback_summary(result, log_file):

    print("\n========== ROLLBACK SUMMARY ==========\n")

    print(f"Status      : {result['status']}")
    print(f"Executed By : {get_current_user()}")
    print(
        f"Work Item   : {result['work_item']} - "
        f"{result.get('work_item_title', 'N/A')}"
    )

    if result["status"] == "SUCCESS":

        if result.get("feature_pr"):
            print(f"Feature PR  : {result['feature_pr']}")

        print(f"Rollback PR : {result['rollback_pr']}")
        print(f"Branch      : {result['branch']}")
        print(f"SHA Before  : {result['sha_before'][:12]}...")
        print(f"SHA After   : {result['sha_after'][:12]}...")

    else:
        print(f"Reason      : {result.get('error', 'Unknown error')}")

    print("\n======================================")

    if result["status"] == "SUCCESS":
        print("Rollback completed successfully.")
    else:
        print("Rollback failed.")

    print("======================================")
    print(f"\nDetailed Log : {log_file}")