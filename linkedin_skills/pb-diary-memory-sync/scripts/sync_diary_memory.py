#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path("/Users/maxkiyuna/Library/CloudStorage/OneDrive-MCPAssetManagementCoLtd/Documents/Taishi Lab/VibeCode/PB")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh PersonalBrand diary memory from Notion")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Path to the PersonalBrand repo root")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    command = [sys.executable, "-m", "personalbrand.cli", "diary-sync"]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        return completed.returncode

    payload = json.loads(completed.stdout)
    summary = {
        "repo_root": str(repo_root),
        "snapshot_path": payload.get("snapshot_path"),
        "fetched_entries": payload.get("fetched_entries"),
        "profile_path": payload.get("render", {}).get("profile_path"),
        "recent_path": payload.get("render", {}).get("recent_path"),
        "db_path": payload.get("render", {}).get("db_path"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
