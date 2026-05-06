import json
import sqlite3
from typing import Optional

from .models import ContentDraft, Framework, StoryNode


def get_story_nodes(conn: sqlite3.Connection, limit: int = 20) -> list[StoryNode]:
    rows = conn.execute(
        """
        SELECT id, title, user_state, conflict_node, desired_outcome,
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
            title=r["title"] or "",
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
        SELECT id, name, hook_type, tone, paragraph_style, cta,
               argument_pattern, fits_topics
        FROM frameworks
        """
    ).fetchall()
    return [
        Framework(
            id=r["id"],
            name=r["name"] or "",
            hook_type=r["hook_type"] or "",
            tone=r["tone"] or "",
            paragraph_style=r["paragraph_style"] or "",
            cta=r["cta"] or "",
            argument_pattern=r["argument_pattern"] or "",
            fits_topics=_parse_json_list(r["fits_topics"]),
        )
        for r in rows
    ]


def get_chunks_for_story(conn: sqlite3.Connection, story_node_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT chunk_text FROM chunks WHERE story_node_id = ? ORDER BY chunk_index",
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
