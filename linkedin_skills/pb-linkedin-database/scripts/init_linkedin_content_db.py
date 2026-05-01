#!/usr/bin/env python3
"""
Initialize the PersonalBrand LinkedIn content SQLite database.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS content_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT NOT NULL,
    source_tab TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    channel TEXT,
    title TEXT,
    brief TEXT,
    category TEXT,
    review_decision TEXT,
    production_status TEXT,
    proposal_id TEXT,
    planner_source TEXT,
    draft_due TEXT,
    review_due TEXT,
    scheduled_date TEXT,
    draft_doc TEXT,
    publish_status TEXT,
    published_date TEXT,
    published_url TEXT,
    linkedin_post_urn TEXT,
    linkedin_author_urn TEXT,
    manager_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_system, source_tab, source_row)
);

CREATE TABLE IF NOT EXISTS planner_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT NOT NULL,
    source_tab TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    slot_label TEXT,
    title TEXT,
    angle TEXT,
    narrative_spine TEXT,
    source_fit TEXT,
    core_tension TEXT,
    opening_scene TEXT,
    notes TEXT,
    draft_due TEXT,
    review_due TEXT,
    scheduled_date TEXT,
    production_status TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_system, source_tab, source_row)
);

CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_item_id INTEGER NOT NULL,
    review_decision TEXT,
    title_at_review TEXT,
    brief_at_review TEXT,
    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT,
    notes TEXT,
    FOREIGN KEY(content_item_id) REFERENCES content_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_item_id INTEGER NOT NULL,
    snapshot_at TEXT NOT NULL,
    source TEXT NOT NULL,
    impressions INTEGER,
    views INTEGER,
    clicks INTEGER,
    reactions INTEGER,
    comments INTEGER,
    reposts INTEGER,
    engagement_rate REAL,
    raw_payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(content_item_id) REFERENCES content_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    details_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_content_items_channel ON content_items(channel);
CREATE INDEX IF NOT EXISTS idx_content_items_review ON content_items(review_decision);
CREATE INDEX IF NOT EXISTS idx_content_items_production_status ON content_items(production_status);
CREATE INDEX IF NOT EXISTS idx_content_items_proposal_id ON content_items(proposal_id);
CREATE INDEX IF NOT EXISTS idx_content_items_linkedin_post ON content_items(linkedin_post_urn);
CREATE INDEX IF NOT EXISTS idx_planner_slots_tab ON planner_slots(source_tab);
CREATE INDEX IF NOT EXISTS idx_snapshots_item_time ON performance_snapshots(content_item_id, snapshot_at);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Path to the SQLite database file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

    print(f"initialized_db={db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
