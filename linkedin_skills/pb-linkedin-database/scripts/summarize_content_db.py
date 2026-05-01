#!/usr/bin/env python3
"""
Summarize the LinkedIn content SQLite database for analyst review.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def fetch_rows(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    cursor = conn.execute(query, params)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def summarize(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        summary = {
            "content_counts": fetch_rows(
                conn,
                """
                SELECT COALESCE(review_decision, '') AS review_decision, COUNT(*) AS count
                FROM content_items
                GROUP BY COALESCE(review_decision, '')
                ORDER BY count DESC
                """,
            ),
            "category_counts": fetch_rows(
                conn,
                """
                SELECT COALESCE(category, '') AS category, COUNT(*) AS count
                FROM content_items
                GROUP BY COALESCE(category, '')
                ORDER BY count DESC, category ASC
                LIMIT 10
                """,
            ),
            "planner_slots": fetch_rows(
                conn,
                """
                SELECT source_tab, COUNT(*) AS count
                FROM planner_slots
                GROUP BY source_tab
                ORDER BY count DESC
                """,
            ),
            "top_impressions": fetch_rows(
                conn,
                """
                SELECT c.title, c.category, p.impressions, p.engagement_rate, p.snapshot_at
                FROM performance_snapshots p
                JOIN content_items c ON c.id = p.content_item_id
                ORDER BY COALESCE(p.impressions, 0) DESC, p.snapshot_at DESC
                LIMIT 5
                """,
            ),
            "latest_syncs": fetch_rows(
                conn,
                """
                SELECT source, action, status, finished_at
                FROM sync_runs
                ORDER BY id DESC
                LIMIT 10
                """,
            ),
        }
    finally:
        conn.close()
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Path to the SQLite database file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = summarize(Path(args.db).expanduser().resolve())
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
