import json
import os
from datetime import datetime


class AuditReport:
    def __init__(self):
        self.results = []

    def add_result(self, result):
        self.results.append(result)

    def finalize(self):
        os.makedirs("logs", exist_ok=True)

        file_path = f"logs/audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(file_path, "w") as f:
            json.dump(self.results, f, indent=2)

        return file_path, self.results