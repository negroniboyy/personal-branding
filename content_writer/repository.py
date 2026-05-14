import json
import sqlite3
from typing import Optional

from .models import ContentDraft, Framework, StoryNode


def get_story_nodes(conn: sqlite3.Connection, limit: int = 20) -> list[StoryNode]:
    rows = conn.execute(
        """
        SELECT id, conflict_node, user_state, desired_outcome,
               the_bridge, thematic_tags, worth_score
        FROM story_nodes
        ORDER BY worth_score DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        StoryNode(
            id=r["id"],
            title=r["conflict_node"] or "",
            user_state=r["user_state"] or "",
            conflict_node=r["conflict_node"] or "",
            desired_outcome=r["desired_outcome"] or "",
            the_bridge=r["the_bridge"] or "",
            thematic_tags=_parse_json_list(r["thematic_tags"]),
            worth_score=r["worth_score"] or 0.0,
        )
        for r in rows
    ]


def get_frameworks(conn: sqlite3.Connection) -> list[Framework]:
    rows = conn.execute(
        """
        SELECT id, source_file, hook_type, tone, paragraph_style, cta_type,
               structure_json, fits_topics, description
        FROM frameworks
        """
    ).fetchall()
    return [
        Framework(
            id=r["id"],
            name=r["source_file"] or r["id"],
            hook_type=r["hook_type"] or "",
            tone=r["tone"] or "",
            paragraph_style=r["paragraph_style"] or "",
            cta=r["cta_type"] or "",
            argument_pattern=r["structure_json"] or "",
            fits_topics=_parse_json_list(r["fits_topics"]),
            description=r["description"] or "",
        )
        for r in rows
    ]


def get_chunks_for_story(conn: sqlite3.Connection, story_node_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT c.chunk_text FROM chunks c
        JOIN story_nodes sn ON sn.page_id = c.page_id
        WHERE sn.id = ?
        ORDER BY c.chunk_index
        """,
        (story_node_id,),
    ).fetchall()
    return [r["chunk_text"] for r in rows if r["chunk_text"]]


def get_latest_weekly_index(conn: sqlite3.Connection) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM weekly_index ORDER BY week_start DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return dict(row)


def save_draft(conn: sqlite3.Connection, draft: ContentDraft) -> int:
    cur = conn.execute(
        """
        INSERT INTO content_drafts (story_node_id, framework_id, idea_prompt,
                                    generated_text, model_used)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            draft.story_node_id,
            draft.framework_id,
            draft.idea_prompt,
            draft.generated_text,
            draft.model_used,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_drafts(conn: sqlite3.Connection, limit: int = 20) -> list[ContentDraft]:
    rows = conn.execute(
        """
        SELECT id, story_node_id, framework_id, idea_prompt,
               generated_text, model_used, created_at
        FROM content_drafts
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_row_to_draft(r) for r in rows]


def update_draft(conn: sqlite3.Connection, draft_id: int, generated_text: str) -> Optional[ContentDraft]:
    conn.execute(
        "UPDATE content_drafts SET generated_text = ? WHERE id = ?",
        (generated_text, draft_id),
    )
    conn.commit()
    return get_draft(conn, draft_id)


def delete_draft(conn: sqlite3.Connection, draft_id: int) -> bool:
    cur = conn.execute("DELETE FROM content_drafts WHERE id = ?", (draft_id,))
    conn.commit()
    return cur.rowcount > 0


def get_draft(conn: sqlite3.Connection, draft_id: int) -> Optional[ContentDraft]:
    row = conn.execute(
        """
        SELECT id, story_node_id, framework_id, idea_prompt,
               generated_text, model_used, created_at
        FROM content_drafts WHERE id = ?
        """,
        (draft_id,),
    ).fetchone()
    return _row_to_draft(row) if row else None


def _row_to_draft(r: sqlite3.Row) -> ContentDraft:
    return ContentDraft(
        id=r["id"],
        story_node_id=r["story_node_id"],
        framework_id=r["framework_id"],
        idea_prompt=r["idea_prompt"],
        generated_text=r["generated_text"],
        model_used=r["model_used"],
        created_at=r["created_at"],
    )


def _parse_json_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return [s.strip() for s in str(value).split(",") if s.strip()]
