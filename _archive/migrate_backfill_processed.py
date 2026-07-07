#!/usr/bin/env python3
"""
Layer 1 migration — one-time run.
Marks pages as processed_status=1 if a story_node already exists for that page_id.
Safe to re-run: only touches pages currently at status=0.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

before = conn.execute("SELECT COUNT(*) FROM pages WHERE processed_status = 0").fetchone()[0]

result = conn.execute("""
    UPDATE pages
    SET processed_status = 1
    WHERE processed_status = 0
      AND EXISTS (
          SELECT 1 FROM story_nodes sn WHERE sn.page_id = pages.id
      )
""")
conn.commit()

after = conn.execute("SELECT COUNT(*) FROM pages WHERE processed_status = 0").fetchone()[0]

print(f"Backfill complete.")
print(f"  Marked done : {result.rowcount} pages")
print(f"  Still queued: {after} pages (genuinely unprocessed — no story_node yet)")
conn.close()
