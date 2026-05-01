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
