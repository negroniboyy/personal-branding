# Blueprint v1.0 — Part 3/4: database.py
# Notion Diary → SQLite Sync

**Prereq:** Parts 1 and 2 must be done first.
**File to create:** `src/notion_fetcher/database.py`

---

## src/notion_fetcher/database.py

```python
import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS pages (
    id                  TEXT PRIMARY KEY,
    title               TEXT,
    created_time        TEXT,
    last_edited_time    TEXT,
    url                 TEXT,
    raw_properties_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
    id             TEXT PRIMARY KEY,
    page_id        TEXT NOT NULL,
    block_type     TEXT NOT NULL,
    plain_text     TEXT,
    raw_block_json TEXT NOT NULL,
    position       INTEGER NOT NULL,
    FOREIGN KEY (page_id) REFERENCES pages(id)
);

CREATE INDEX IF NOT EXISTS idx_blocks_page_id ON blocks(page_id);

CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,
    page_id     TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text  TEXT NOT NULL,
    FOREIGN KEY (page_id) REFERENCES pages(id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_page_id ON chunks(page_id);
"""


def _extract_title(properties: dict) -> str:
    for prop_value in properties.values():
        if prop_value.get("type") == "title":
            return "".join(rt.get("plain_text", "") for rt in prop_value.get("title", []))
    return ""


def _extract_plain_text(block: dict) -> str | None:
    block_type = block.get("type", "")
    block_content = block.get(block_type, {})
    if not isinstance(block_content, dict):
        return None
    rich_text = block_content.get("rich_text", [])
    if not rich_text:
        return None
    return "".join(rt.get("plain_text", "") for rt in rich_text)


class Database:

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_DDL)
        self.conn.commit()

    def upsert_page(self, page_dict: dict):
        page_id = page_dict["id"]
        title = _extract_title(page_dict["properties"])
        self.conn.execute(
            "INSERT OR REPLACE INTO pages "
            "(id, title, created_time, last_edited_time, url, raw_properties_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                page_id,
                title,
                page_dict.get("created_time", ""),
                page_dict.get("last_edited_time", ""),
                page_dict.get("url", ""),
                json.dumps(page_dict["properties"]),
            ),
        )
        self.conn.commit()

    def upsert_blocks(self, page_id: str, blocks: list[dict]):
        self.conn.execute("DELETE FROM blocks WHERE page_id = ?", (page_id,))
        for position, block in enumerate(blocks):
            self.conn.execute(
                "INSERT INTO blocks "
                "(id, page_id, block_type, plain_text, raw_block_json, position) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    block["id"],
                    page_id,
                    block["type"],
                    _extract_plain_text(block),
                    json.dumps(block),
                    position,
                ),
            )
        self.conn.commit()

    def upsert_chunks(self, page_id: str, chunks: list[str]):
        self.conn.execute("DELETE FROM chunks WHERE page_id = ?", (page_id,))
        for chunk_index, chunk_text in enumerate(chunks):
            self.conn.execute(
                "INSERT INTO chunks (id, page_id, chunk_index, chunk_text) VALUES (?, ?, ?, ?)",
                (f"{page_id}_{chunk_index}", page_id, chunk_index, chunk_text),
            )
        self.conn.commit()

    def delete_stale_pages(self, live_page_ids: set[str]):
        """Delete pages (+ their blocks/chunks) no longer present in Notion."""
        rows = self.conn.execute("SELECT id FROM pages").fetchall()
        stale_ids = {row["id"] for row in rows} - live_page_ids
        for stale_id in stale_ids:
            logger.info(f"Deleting stale page: {stale_id}")
            self.conn.execute("DELETE FROM chunks WHERE page_id = ?", (stale_id,))
            self.conn.execute("DELETE FROM blocks WHERE page_id = ?", (stale_id,))
            self.conn.execute("DELETE FROM pages WHERE id = ?", (stale_id,))
        self.conn.commit()
        if stale_ids:
            logger.info(f"Deleted {len(stale_ids)} stale pages.")

    def close(self):
        self.conn.close()
```

---

## DONE FOR PART 3

Feed Part 4 (chunker.py + sync.py + DoD) next.
