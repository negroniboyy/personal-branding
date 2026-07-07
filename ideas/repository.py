import json
import sqlite3
import uuid
from typing import Optional
from .models import Idea, IdeaDraft


def run_migration(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ideas (
            id         TEXT PRIMARY KEY,
            title      TEXT NOT NULL DEFAULT '',
            body       TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.commit()

    for sql in [
        "ALTER TABLE content_drafts ADD COLUMN idea_id TEXT REFERENCES ideas(id)",
        "ALTER TABLE reel_scripts   ADD COLUMN idea_id TEXT REFERENCES ideas(id)",
        "ALTER TABLE ideas ADD COLUMN notion_page_id TEXT",
        "ALTER TABLE ideas ADD COLUMN pillar TEXT",
        "ALTER TABLE ideas ADD COLUMN tier TEXT",
        "ALTER TABLE ideas ADD COLUMN channels TEXT",
        "ALTER TABLE ideas ADD COLUMN notion_last_status TEXT",
        "ALTER TABLE ideas ADD COLUMN notion_synced_at TEXT",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists or table not yet created

    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ideas_notion_page_id "
            "ON ideas(notion_page_id) WHERE notion_page_id IS NOT NULL"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass


def create_idea(conn: sqlite3.Connection, idea_id: str, now: str) -> Idea:
    conn.execute(
        "INSERT INTO ideas (id, title, body, created_at, updated_at) VALUES (?, '', '', ?, ?)",
        (idea_id, now, now),
    )
    conn.commit()
    return Idea(id=idea_id, title="", body="", draft_count=0, created_at=now, updated_at=now)


def _row_to_idea(row: sqlite3.Row) -> Idea:
    d = dict(row)
    d["channels"] = json.loads(d["channels"]) if d.get("channels") else []
    return Idea(**d)


def list_ideas(conn: sqlite3.Connection) -> list[Idea]:
    rows = conn.execute("""
        SELECT i.id, i.title, i.body, i.created_at, i.updated_at,
               i.notion_page_id, i.pillar, i.tier, i.channels,
               (SELECT COUNT(*) FROM content_drafts cd WHERE cd.idea_id = i.id)
               + (SELECT COUNT(*) FROM reel_scripts rs WHERE rs.idea_id = i.id) AS draft_count
        FROM ideas i
        ORDER BY i.updated_at DESC
    """).fetchall()
    return [_row_to_idea(r) for r in rows]


def get_idea(conn: sqlite3.Connection, idea_id: str) -> Optional[Idea]:
    row = conn.execute("""
        SELECT i.id, i.title, i.body, i.created_at, i.updated_at,
               i.notion_page_id, i.pillar, i.tier, i.channels,
               (SELECT COUNT(*) FROM content_drafts cd WHERE cd.idea_id = i.id)
               + (SELECT COUNT(*) FROM reel_scripts rs WHERE rs.idea_id = i.id) AS draft_count
        FROM ideas i WHERE i.id = ?
    """, (idea_id,)).fetchone()
    if not row:
        return None
    return _row_to_idea(row)


def upsert_idea_from_notion(
    conn: sqlite3.Connection,
    notion_page_id: str,
    title: str,
    body: str,
    pillar: Optional[str],
    tier: Optional[str],
    channels: list[str],
    now: str,
) -> tuple[str, bool]:
    """Insert or update an idea keyed by notion_page_id. Notion wins for content —
    title/body/pillar/tier/channels are always overwritten from the Notion row.
    Returns (idea_id, created)."""
    existing = conn.execute(
        "SELECT id FROM ideas WHERE notion_page_id = ?", (notion_page_id,)
    ).fetchone()
    channels_json = json.dumps(channels)

    if existing:
        idea_id = existing["id"]
        conn.execute(
            "UPDATE ideas SET title = ?, body = ?, pillar = ?, tier = ?, channels = ?, "
            "updated_at = ? WHERE id = ?",
            (title, body, pillar, tier, channels_json, now, idea_id),
        )
        conn.commit()
        return idea_id, False

    idea_id = "idea_" + uuid.uuid4().hex[:8]
    conn.execute(
        "INSERT INTO ideas (id, title, body, created_at, updated_at, notion_page_id, "
        "pillar, tier, channels) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (idea_id, title, body, now, now, notion_page_id, pillar, tier, channels_json),
    )
    conn.commit()
    return idea_id, True


def derive_idea_status(conn: sqlite3.Connection, idea_id: str) -> str:
    """No own status column on ideas — status is derived from linked drafts'
    lifecycle. Rule: no drafts -> queued; all drafts killed -> killed; else the
    furthest stage reached among non-killed drafts (posted > recorded > approved > drafted).
    Reels are versioned per idea — only the LIVE version (highest version among
    non-killed rows) contributes its status, so a stale superseded version can't
    keep the idea pinned to an old stage."""
    statuses = [
        (r["status"] or "queued") for r in conn.execute(
            "SELECT status FROM content_drafts WHERE idea_id = ?", (idea_id,)
        ).fetchall()
    ]

    live_reel = conn.execute(
        "SELECT status FROM reel_scripts WHERE idea_id = ? AND status != 'killed' "
        "ORDER BY version DESC LIMIT 1",
        (idea_id,),
    ).fetchone()
    if live_reel:
        statuses.append(live_reel["status"] or "queued")
    elif conn.execute("SELECT 1 FROM reel_scripts WHERE idea_id = ? LIMIT 1", (idea_id,)).fetchone():
        # every reel version for this idea is killed -> the leg contributes "killed"
        statuses.append("killed")

    if not statuses:
        return "queued"
    if all(s == "killed" for s in statuses):
        return "killed"
    active = [s for s in statuses if s != "killed"]
    for stage in ("posted", "recorded", "approved"):
        if stage in active:
            return stage
    return "drafted"


def patch_idea(conn: sqlite3.Connection, idea_id: str, title: Optional[str], body: Optional[str], now: str) -> None:
    if title is not None:
        conn.execute("UPDATE ideas SET title = ?, updated_at = ? WHERE id = ?", (title, now, idea_id))
    if body is not None:
        conn.execute("UPDATE ideas SET body = ?, updated_at = ? WHERE id = ?", (body, now, idea_id))
    conn.commit()


def set_idea_tier(conn: sqlite3.Connection, idea_id: str, tier: str, now: str) -> None:
    """Tier is a PBS-side production decision — settable even for Notion-linked
    ideas (unlike title/body, which stay read-only once synced)."""
    conn.execute("UPDATE ideas SET tier = ?, updated_at = ? WHERE id = ?", (tier, now, idea_id))
    conn.commit()


def get_idea_drafts(conn: sqlite3.Connection, idea_id: str) -> list[IdeaDraft]:
    drafts: list[IdeaDraft] = []

    linkedin_rows = conn.execute("""
        SELECT id, framework_id, story_node_id, generated_text, model_used, created_at,
               framework_pick_reason
        FROM content_drafts WHERE idea_id = ?
        ORDER BY created_at DESC
    """, (idea_id,)).fetchall()
    for r in linkedin_rows:
        drafts.append(IdeaDraft(
            id=r["id"], channel="linkedin",
            generated_text=r["generated_text"],
            framework_id=str(r["framework_id"]) if r["framework_id"] else None,
            framework_pick_reason=r["framework_pick_reason"],
            story_node_id=str(r["story_node_id"]) if r["story_node_id"] else None,
            model_used=r["model_used"],
            created_at=r["created_at"],
        ))

    reel_rows = conn.execute("""
        SELECT id, framework_id, story_node_id, generated_text, model_used, created_at,
               framework_pick_reason, version, tier
        FROM reel_scripts WHERE idea_id = ?
        ORDER BY version DESC
    """, (idea_id,)).fetchall()
    for r in reel_rows:
        drafts.append(IdeaDraft(
            id=r["id"], channel="reel",
            generated_text=r["generated_text"],
            framework_id=str(r["framework_id"]) if r["framework_id"] else None,
            framework_pick_reason=r["framework_pick_reason"],
            story_node_id=str(r["story_node_id"]) if r["story_node_id"] else None,
            model_used=r["model_used"],
            created_at=r["created_at"],
            version=r["version"] or 1,
            tier=r["tier"],
        ))

    drafts.sort(key=lambda d: d.created_at, reverse=True)
    return drafts


def link_draft(conn: sqlite3.Connection, draft_id: int, idea_id: str) -> None:
    conn.execute("UPDATE content_drafts SET idea_id = ? WHERE id = ?", (idea_id, draft_id))
    conn.commit()


def link_reel(conn: sqlite3.Connection, script_id: int, idea_id: str) -> None:
    conn.execute("UPDATE reel_scripts SET idea_id = ? WHERE id = ?", (idea_id, script_id))
    conn.commit()


def delete_idea_cascade(conn: sqlite3.Connection, idea_id: str) -> dict:
    """Delete idea and all linked drafts/scripts in one transaction. Returns counts."""
    with conn:
        drafts_removed = conn.execute(
            "DELETE FROM content_drafts WHERE idea_id = ?", (idea_id,)
        ).rowcount
        scripts_removed = conn.execute(
            "DELETE FROM reel_scripts WHERE idea_id = ?", (idea_id,)
        ).rowcount
        ideas_removed = conn.execute(
            "DELETE FROM ideas WHERE id = ?", (idea_id,)
        ).rowcount
    return {
        "deleted": ideas_removed > 0,
        "drafts_removed": drafts_removed,
        "scripts_removed": scripts_removed,
    }


def delete_linkedin_draft(conn: sqlite3.Connection, idea_id: str, draft_id: int) -> bool:
    """Delete a single LinkedIn draft scoped to its parent idea."""
    with conn:
        rowcount = conn.execute(
            "DELETE FROM content_drafts WHERE id = ? AND idea_id = ?", (draft_id, idea_id)
        ).rowcount
    return rowcount > 0


def delete_reel_script(conn: sqlite3.Connection, idea_id: str, script_id: int) -> bool:
    """Delete a single Reel script scoped to its parent idea."""
    with conn:
        rowcount = conn.execute(
            "DELETE FROM reel_scripts WHERE id = ? AND idea_id = ?", (script_id, idea_id)
        ).rowcount
    return rowcount > 0
