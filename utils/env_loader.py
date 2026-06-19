import os
from pathlib import Path

def load_env():
    base_dir = Path(__file__).resolve().parent.parent
    env_path = base_dir / ".env"

    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                os.environ.setdefault(
                    key.strip(),
                    value.strip().strip('"').strip("'")
                )