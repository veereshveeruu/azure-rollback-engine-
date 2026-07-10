import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any


AUDIT_DIR = "audit_reports"


class AuditReport:
    """Handles rollback execution audit report generation."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add_result(self, result: Dict[str, Any]) -> None:
        """Add rollback execution result."""
        self.results.append(result)

    def _generate_audit_filename(self) -> str:
        """Generate audit filename with date, work item(s), and sequence."""

        today = datetime.now().strftime("%Y%m%d")

        # Get all work item IDs
        work_items = {
            str(result["work_item"]).split(" - ")[0]
            for result in self.results
        }

        # Single or multiple work items
        if len(work_items) == 1:
            identifier = f"WI{next(iter(work_items))}"
        else:
            identifier = "MULTI"

        pattern = re.compile(
            rf"audit_{today}_{identifier}_(\d{{3}})\.json"
        )

        sequences = []

        if os.path.exists(AUDIT_DIR):
            for filename in os.listdir(AUDIT_DIR):
                match = pattern.match(filename)
                if match:
                    sequences.append(int(match.group(1)))

        next_sequence = max(sequences, default=0) + 1

        return (
            f"audit_{today}_{identifier}_{next_sequence:03d}.json"
        )

    def finalize(self) -> tuple[str, List[Dict[str, Any]]]:
        """Generate JSON audit report."""

        os.makedirs(AUDIT_DIR, exist_ok=True)

        filename = self._generate_audit_filename()

        file_path = os.path.join(
            AUDIT_DIR,
            filename
        )

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.results,
                file,
                indent=2
            )

        return file_path, self.results