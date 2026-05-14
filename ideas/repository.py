import sqlite3
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
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists or table not yet created


def create_idea(conn: sqlite3.Connection, idea_id: str, now: str) -> Idea:
    conn.execute(
        "INSERT INTO ideas (id, title, body, created_at, updated_at) VALUES (?, '', '', ?, ?)",
        (idea_id, now, now),
    )
    conn.commit()
    return Idea(id=idea_id, title="", body="", draft_count=0, created_at=now, updated_at=now)


def list_ideas(conn: sqlite3.Connection) -> list[Idea]:
    rows = conn.execute("""
        SELECT i.id, i.title, i.body, i.created_at, i.updated_at,
               (SELECT COUNT(*) FROM content_drafts cd WHERE cd.idea_id = i.id)
               + (SELECT COUNT(*) FROM reel_scripts rs WHERE rs.idea_id = i.id) AS draft_count
        FROM ideas i
        ORDER BY i.updated_at DESC
    """).fetchall()
    return [Idea(**dict(r)) for r in rows]


def get_idea(conn: sqlite3.Connection, idea_id: str) -> Optional[Idea]:
    row = conn.execute("""
        SELECT i.id, i.title, i.body, i.created_at, i.updated_at,
               (SELECT COUNT(*) FROM content_drafts cd WHERE cd.idea_id = i.id)
               + (SELECT COUNT(*) FROM reel_scripts rs WHERE rs.idea_id = i.id) AS draft_count
        FROM ideas i WHERE i.id = ?
    """, (idea_id,)).fetchone()
    if not row:
        return None
    return Idea(**dict(row))


def patch_idea(conn: sqlite3.Connection, idea_id: str, title: Optional[str], body: Optional[str], now: str) -> None:
    if title is not None:
        conn.execute("UPDATE ideas SET title = ?, updated_at = ? WHERE id = ?", (title, now, idea_id))
    if body is not None:
        conn.execute("UPDATE ideas SET body = ?, updated_at = ? WHERE id = ?", (body, now, idea_id))
    conn.commit()


def get_idea_drafts(conn: sqlite3.Connection, idea_id: str) -> list[IdeaDraft]:
    drafts: list[IdeaDraft] = []

    linkedin_rows = conn.execute("""
        SELECT id, framework_id, story_node_id, generated_text, model_used, created_at
        FROM content_drafts WHERE idea_id = ?
        ORDER BY created_at DESC
    """, (idea_id,)).fetchall()
    for r in linkedin_rows:
        drafts.append(IdeaDraft(
            id=r["id"], channel="linkedin",
            generated_text=r["generated_text"],
            framework_id=str(r["framework_id"]) if r["framework_id"] else None,
            story_node_id=str(r["story_node_id"]) if r["story_node_id"] else None,
            model_used=r["model_used"],
            created_at=r["created_at"],
        ))

    reel_rows = conn.execute("""
        SELECT id, framework_id, story_node_id, generated_text, model_used, created_at
        FROM reel_scripts WHERE idea_id = ?
        ORDER BY created_at DESC
    """, (idea_id,)).fetchall()
    for r in reel_rows:
        drafts.append(IdeaDraft(
            id=r["id"], channel="reel",
            generated_text=r["generated_text"],
            framework_id=str(r["framework_id"]) if r["framework_id"] else None,
            story_node_id=str(r["story_node_id"]) if r["story_node_id"] else None,
            model_used=r["model_used"],
            created_at=r["created_at"],
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
