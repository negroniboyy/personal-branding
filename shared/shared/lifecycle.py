"""Content lifecycle shared by reel_scripts and content_drafts.

Status flow: queued -> approved -> recorded (reels only) -> posted.
Terminal alternative: killed.
"""

import sqlite3
from typing import Optional

STATUSES = ("queued", "approved", "recorded", "posted", "killed")

# Columns PATCHable via the /meta endpoints.
META_COLUMNS = ("status", "verdict", "verdict_note", "asana_task_gid")

LIFECYCLE_COLUMNS_SQL = [
    "ALTER TABLE {table} ADD COLUMN status TEXT DEFAULT 'queued'",
    "ALTER TABLE {table} ADD COLUMN verdict INTEGER",
    "ALTER TABLE {table} ADD COLUMN verdict_note TEXT",
    "ALTER TABLE {table} ADD COLUMN caption TEXT",
    "ALTER TABLE {table} ADD COLUMN cta TEXT",
    "ALTER TABLE {table} ADD COLUMN asana_task_gid TEXT",
    "ALTER TABLE {table} ADD COLUMN posted_at TEXT",
]


def migrate_lifecycle_columns(conn: sqlite3.Connection, table: str) -> None:
    for alter in LIFECYCLE_COLUMNS_SQL:
        try:
            conn.execute(alter.format(table=table))
        except Exception:
            pass
    conn.commit()


def update_meta(conn: sqlite3.Connection, table: str, item_id: int, fields: dict) -> Optional[dict]:
    """Apply a whitelisted partial update; returns the full updated row or None."""
    updates = {k: v for k, v in fields.items() if k in META_COLUMNS and v is not None}
    if "status" in updates:
        if updates["status"] not in STATUSES:
            raise ValueError(f"invalid status {updates['status']!r}; must be one of {STATUSES}")
        if updates["status"] == "posted":
            updates["posted_at"] = None  # placeholder, set via SQL below
    row = conn.execute(f"SELECT id FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return None
    if updates:
        set_parts, params = [], []
        for col, val in updates.items():
            if col == "posted_at":
                set_parts.append("posted_at = datetime('now')")
            else:
                set_parts.append(f"{col} = ?")
                params.append(val)
        params.append(item_id)
        conn.execute(f"UPDATE {table} SET {', '.join(set_parts)} WHERE id = ?", params)
        conn.commit()
    updated = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    return dict(updated)


def save_package(conn: sqlite3.Connection, table: str, item_id: int, caption: str, cta: str) -> None:
    conn.execute(
        f"UPDATE {table} SET caption = ?, cta = ? WHERE id = ?",
        (caption, cta, item_id),
    )
    conn.commit()


def get_feedback_block(conn: sqlite3.Connection, table: str, limit: int = 6) -> str:
    """Recent editorial verdicts as a prompt block, or '' if none exist."""
    try:
        rows = conn.execute(
            f"""
            SELECT verdict, verdict_note FROM {table}
            WHERE verdict_note IS NOT NULL AND verdict_note != ''
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except Exception:
        return ""
    if not rows:
        return ""
    lines = []
    for r in rows:
        prefix = "KEEP DOING" if (r["verdict"] or 0) >= 0 else "AVOID"
        lines.append(f"- {prefix}: {r['verdict_note']}")
    return (
        "\n\nRECENT EDITORIAL FEEDBACK (from the author's reviews of past drafts — "
        "follow these notes):\n" + "\n".join(lines)
    )


CAPTION_PROMPT = """You are packaging an already-approved piece of content for publishing.
Do NOT rewrite the content. Based on it, produce:
1. A short platform caption (2-3 sentences max, same voice as the content, 3-5 relevant hashtags at the end).
2. A one-line call to action.

Output EXACTLY this format, nothing else:
CAPTION:
<caption text>
CTA:
<one line cta>

CONTENT:
{content}
"""


def parse_package_output(text: str) -> tuple[str, str]:
    """Parse 'CAPTION: ... CTA: ...' markers; tolerant of missing CTA."""
    caption, cta = text.strip(), ""
    upper = text.upper()
    if "CAPTION:" in upper:
        start = upper.index("CAPTION:") + len("CAPTION:")
        if "CTA:" in upper[start:]:
            cta_idx = upper.index("CTA:", start)
            caption = text[start:cta_idx].strip()
            cta = text[cta_idx + len("CTA:"):].strip()
        else:
            caption = text[start:].strip()
    return caption, cta
