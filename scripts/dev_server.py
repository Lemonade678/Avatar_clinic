"""Run the app on this computer without LINE (dev mode, in-memory data from the CSV files).

Usage (PowerShell or Git Bash): .venv/Scripts/python scripts/dev_server.py [port]
Then open http://localhost:8000 — data is lost when the server stops.
"""
import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> None:
    os.chdir(ROOT)  # config.yaml and data/ are relative to the repo root
    os.environ.setdefault("APP_ENV", "dev")
    os.environ.setdefault("DEV_USER_ID", "U-dev")
    port = int(argv[1]) if len(argv) > 1 else 8000
    uvicorn.run("stockcount.app:build_default_app", factory=True, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main(sys.argv)
