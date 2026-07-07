"""Two-way sync between the Notion CONTENT database and the PBS `ideas` table.

Notion wins for idea content (pull); PBS wins for lifecycle status (push).
Business logic only — no FastAPI/UI here (root CLAUDE.md rule); routes.py and
jobs/handlers.py just call pull_ideas()/push_status().
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from ideas import repository as ideas_repository

from . import config
from .mapper import LIFECYCLE_TO_NOTION_STATUS, blocks_to_text, page_to_idea_fields

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NOTION_FETCHER_SRC = _REPO_ROOT / "NOTION DIARY FETCHER" / "src"
if str(_NOTION_FETCHER_SRC) not in sys.path:
    sys.path.insert(0, str(_NOTION_FETCHER_SRC))

from notion_fetcher.client import NotionClient  # noqa: E402 — depends on the sys.path insert above


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client() -> NotionClient:
    return NotionClient(token=config.get_notion_token())


def pull_ideas(conn: sqlite3.Connection) -> dict:
    """Pull every row from the Notion CONTENT database into `ideas`, upserting
    by notion_page_id. Never deletes — a row removed in Notion just stops
    updating. Notion's own status is ignored here; PBS owns status (push_status)."""
    client = _client()
    database_id = config.get_ideas_database_id()
    pages = client.get_all_database_pages(database_id)

    created = updated = 0
    now = _now()
    for page in pages:
        fields = page_to_idea_fields(page)
        if not fields["body"].strip():
            # Description is empty — most ideas are actually written in the page
            # body, not that property. Fall back to flattened block text.
            blocks = client.get_page_blocks(fields["notion_page_id"])
            fields["body"] = blocks_to_text(blocks)
        _, was_created = ideas_repository.upsert_idea_from_notion(
            conn,
            notion_page_id=fields["notion_page_id"],
            title=fields["title"],
            body=fields["body"],
            pillar=fields["pillar"],
            tier=fields["tier"],
            channels=fields["channels"],
            now=now,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {"pulled": len(pages), "created": created, "updated": updated}


def push_status(conn: sqlite3.Connection, idea_id: str) -> dict:
    """Push this idea's derived lifecycle status to its linked Notion row, if
    it changed since the last successful push. No-op for local-only ideas."""
    row = conn.execute(
        "SELECT notion_page_id, notion_last_status FROM ideas WHERE id = ?", (idea_id,)
    ).fetchone()
    if not row or not row["notion_page_id"]:
        return {"skipped": True, "reason": "idea has no linked Notion page"}

    status = ideas_repository.derive_idea_status(conn, idea_id)
    if status == row["notion_last_status"]:
        return {"skipped": True, "reason": "status unchanged", "status": status}

    mapped = LIFECYCLE_TO_NOTION_STATUS.get(status)
    if not mapped:
        return {"skipped": True, "reason": f"no Notion mapping for status {status!r}"}

    client = _client()
    client.client.pages.update(
        page_id=row["notion_page_id"],
        properties={"status": {"status": {"name": mapped}}},
    )

    conn.execute(
        "UPDATE ideas SET notion_last_status = ?, notion_synced_at = ? WHERE id = ?",
        (status, _now(), idea_id),
    )
    conn.commit()
    return {"pushed": True, "status": status, "notion_status": mapped}
