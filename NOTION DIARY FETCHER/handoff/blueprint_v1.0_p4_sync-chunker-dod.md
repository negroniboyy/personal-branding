# Blueprint v1.0 — Part 4/4: chunker.py + sync.py + DoD
# Notion Diary → SQLite Sync

**Prereq:** Parts 1, 2, 3 must be done first.
**Files to create:** `src/notion_fetcher/chunker.py`, `src/notion_fetcher/sync.py`

---

## src/notion_fetcher/chunker.py

```python
from .database import _extract_plain_text

CHARS_PER_TOKEN = 4


def chunk_page_blocks(
    blocks: list[dict],
    title: str,
    chunk_size_tokens: int = 500,
    overlap_chars: int = 50,
) -> list[str]:
    """Split page blocks into overlapping text chunks prefixed with page title."""
    chunk_size_chars = chunk_size_tokens * CHARS_PER_TOKEN

    text_parts = []
    for block in blocks:
        plain_text = _extract_plain_text(block)
        if plain_text and plain_text.strip():
            text_parts.append(plain_text.strip())

    full_text = "\n\n".join(text_parts)
    if not full_text:
        return []

    prefix = f"[{title}] " if title else ""
    chunks = []
    start = 0

    while start < len(full_text):
        chunk_body = full_text[start : start + chunk_size_chars]
        chunks.append(prefix + chunk_body)
        start += chunk_size_chars - overlap_chars
        if start >= len(full_text):
            break

    return chunks
```

---

## src/notion_fetcher/sync.py

```python
import logging
import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv

from .client import NotionClient
from .chunker import chunk_page_blocks
from .database import Database, _extract_title

logger = logging.getLogger(__name__)


def run_sync(token: str, database_id: str, config: dict):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db_path = config["database"]["path"]
    rate_limit_delay = config["sync"]["rate_limit_delay"]
    chunk_size_tokens = config["sync"]["chunk_size_tokens"]
    overlap_chars = config["sync"]["chunk_overlap_chars"]
    page_size = config["notion"]["page_size"]

    client = NotionClient(token=token, rate_limit_delay=rate_limit_delay)
    db = Database(db_path=db_path)

    try:
        logger.info("Step 1: Fetching all pages from Notion database...")
        pages = client.get_all_database_pages(database_id=database_id, page_size=page_size)
        logger.info(f"Found {len(pages)} pages.")

        live_page_ids = {page["id"] for page in pages}

        for i, page in enumerate(pages):
            page_id = page["id"]
            title = _extract_title(page["properties"])
            logger.info(f"[{i+1}/{len(pages)}] {title or page_id}")

            db.upsert_page(page)

            try:
                blocks = client.get_page_blocks(page_id=page_id)
                logger.info(f"  -> {len(blocks)} blocks")
            except Exception as e:
                logger.error(f"  -> Block fetch failed for {page_id}: {e}")
                continue

            db.upsert_blocks(page_id=page_id, blocks=blocks)

            chunks = chunk_page_blocks(
                blocks=blocks,
                title=title,
                chunk_size_tokens=chunk_size_tokens,
                overlap_chars=overlap_chars,
            )
            db.upsert_chunks(page_id=page_id, chunks=chunks)
            logger.info(f"  -> {len(chunks)} chunks")

        logger.info("Step 2: Pruning stale pages...")
        db.delete_stale_pages(live_page_ids=live_page_ids)

        logger.info("Sync complete.")

    finally:
        db.close()


def main():
    load_dotenv()

    config_path = Path("config.toml")
    if not config_path.exists():
        print("ERROR: config.toml not found")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not token or not database_id:
        print("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID must be set in .env")
        sys.exit(1)

    run_sync(token=token, database_id=database_id, config=config)
```

---

## DEFINITION OF DONE

Confirm ALL before reporting complete:

**Files exist:**
- [ ] pyproject.toml
- [ ] .env.example
- [ ] config.toml
- [ ] .gitignore
- [ ] main.py
- [ ] src/notion_fetcher/__init__.py
- [ ] src/notion_fetcher/client.py
- [ ] src/notion_fetcher/database.py
- [ ] src/notion_fetcher/chunker.py
- [ ] src/notion_fetcher/sync.py

**Code rules:**
- [ ] No hardcoded credentials
- [ ] tomllib used (not toml package)
- [ ] No requirements.txt
- [ ] chunk_text starts with "[title] " prefix
- [ ] chunks.id pattern: "{page_id}_{chunk_index}"
- [ ] WAL pragma set in Database.__init__
- [ ] delete_stale_pages() called in run_sync()
