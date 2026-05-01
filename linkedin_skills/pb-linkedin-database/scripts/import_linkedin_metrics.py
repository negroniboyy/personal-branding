#!/usr/bin/env python3
"""Import LinkedIn performance snapshots from a JSON payload file into SQLite.

Expected JSON shape:
[
  {
    "lookup": {"id": "..."} or {"proposal_id": "..."} or {"linkedin_post_urn": "..."} or {"title": "..."},
    "snapshot_at": "2026-04-03T00:00:00Z",
    "source": "linkedin_member_post_statistics",
    "metrics": {
      "impressions": 100,
      "views": 80,
      "clicks": 5,
      "reactions": 9,
      "comments": 1,
      "reposts": 0,
      "engagement_rate": 0.15
    },
    "raw_payload": {...}
  }
]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


LOOKUP_ORDER = ("id", "proposal_id", "linkedin_post_urn", "title")


def load_payload(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Metrics payload must be a JSON list")
    return payload


def resolve_content_item_id(conn: sqlite3.Connection, lookup: dict) -> int | None:
    for key in LOOKUP_ORDER:
        value = str(lookup.get(key, "")).strip()
        if not value:
            continue
        if key in {"id", "proposal_id"}:
            row = conn.execute("SELECT id FROM content_items WHERE proposal_id = ?", (value,)).fetchone()
        else:
            row = conn.execute(f"SELECT id FROM content_items WHERE {key} = ?", (value,)).fetchone()
        if row:
            return int(row[0])
    return None


def record_sync(conn: sqlite3.Connection, status: str, details: dict) -> None:
    conn.execute(
        """
        INSERT INTO sync_runs (source, action, status, finished_at, details_json)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        """,
        ("linkedin_metrics", "import_linkedin_metrics", status, json.dumps(details, ensure_ascii=False)),
    )


def import_payload(db_path: Path, payload_path: Path) -> dict[str, int]:
    payload = load_payload(payload_path)
    conn = sqlite3.connect(db_path)
    imported = 0
    unmatched = 0
    try:
        for item in payload:
            lookup = item.get("lookup", {})
            content_item_id = resolve_content_item_id(conn, lookup)
            if content_item_id is None:
                unmatched += 1
                continue
            metrics = item.get("metrics", {})
            conn.execute(
                """
                INSERT INTO performance_snapshots (
                    content_item_id, snapshot_at, source, impressions, views, clicks,
                    reactions, comments, reposts, engagement_rate, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_item_id,
                    item.get("snapshot_at"),
                    item.get("source", "linkedin_metrics_import"),
                    metrics.get("impressions"),
                    metrics.get("views"),
                    metrics.get("clicks"),
                    metrics.get("reactions"),
                    metrics.get("comments"),
                    metrics.get("reposts"),
                    metrics.get("engagement_rate"),
                    json.dumps(item.get("raw_payload", item), ensure_ascii=False),
                ),
            )
            imported += 1

        record_sync(
            conn,
            "success",
            {"payload": str(payload_path), "imported": imported, "unmatched": unmatched},
        )
        conn.commit()
    finally:
        conn.close()
    return {"imported": imported, "unmatched": unmatched}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Path to the SQLite database file")
    parser.add_argument("--payload-file", required=True, help="JSON payload file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = import_payload(Path(args.db).expanduser().resolve(), Path(args.payload_file).expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
