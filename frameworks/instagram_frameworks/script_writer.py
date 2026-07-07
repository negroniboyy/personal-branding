#!/usr/bin/env python3
"""
Generate Instagram Reel video scripts from an idea prompt matched to a reel framework.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import llm_client
import yaml
from shared.logger import get_logger

logger = get_logger("instagram_frameworks")

SCRIPT_DIR  = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
IDEA_PROMPT_PATH = PROMPTS_DIR / "script_writer_idea.txt"
VOICE_BLOCK_PATH = SCRIPT_DIR.parent.parent / "brandguide" / "voice_dna_block.txt"

TIER_TEMPLATES = {
    "scripted-headshot": PROMPTS_DIR / "script_writer_idea.txt",
    "raw-talking-head":  PROMPTS_DIR / "script_writer_raw.txt",
    "beat-edit":         PROMPTS_DIR / "script_writer_beat.txt",
}


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def _backfill_reel_descriptions(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, yaml_path FROM reel_frameworks WHERE description IS NULL OR description = ''"
    ).fetchall()
    for row in rows:
        try:
            with open(row["yaml_path"], "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            desc = (data or {}).get("description", "")
            if desc:
                conn.execute(
                    "UPDATE reel_frameworks SET description = ? WHERE id = ?",
                    (desc, row["id"]),
                )
        except Exception:
            pass
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reel_scripts (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            story_node_id       INTEGER NOT NULL,
            framework_id        TEXT NOT NULL,
            idea_prompt         TEXT,
            generated_text      TEXT NOT NULL,
            model_used          TEXT NOT NULL,
            duration_target_sec REAL,
            created_at          TEXT NOT NULL
        );
    """)
    for alter in [
        "ALTER TABLE reel_frameworks ADD COLUMN description TEXT DEFAULT ''",
        "ALTER TABLE reel_scripts ADD COLUMN framework_pick_reason TEXT",
        "ALTER TABLE reel_scripts ADD COLUMN tier TEXT",
        "ALTER TABLE reel_scripts ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE reel_scripts ADD COLUMN parent_script_id INTEGER",
    ]:
        try:
            conn.execute(alter)
        except Exception:
            pass
    conn.commit()
    _make_story_node_nullable(conn)
    from shared.lifecycle import migrate_lifecycle_columns
    migrate_lifecycle_columns(conn, "reel_scripts")
    _backfill_reel_descriptions(conn)


def _make_story_node_nullable(conn: sqlite3.Connection) -> None:
    info = conn.execute("PRAGMA table_info(reel_scripts)").fetchall()
    col = next((r for r in info if r["name"] == "story_node_id"), None)
    if col is None or col["notnull"] == 0:
        return
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reel_scripts_new (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            story_node_id       INTEGER,
            framework_id        TEXT NOT NULL,
            idea_prompt         TEXT,
            generated_text      TEXT NOT NULL,
            model_used          TEXT NOT NULL,
            duration_target_sec REAL,
            created_at          TEXT NOT NULL,
            idea_id             TEXT REFERENCES ideas(id)
        );
        INSERT INTO reel_scripts_new
            SELECT id, story_node_id, framework_id, idea_prompt,
                   generated_text, model_used, duration_target_sec, created_at,
                   CASE WHEN EXISTS(SELECT 1 FROM pragma_table_info('reel_scripts') WHERE name='idea_id')
                        THEN idea_id ELSE NULL END
            FROM reel_scripts;
        DROP TABLE reel_scripts;
        ALTER TABLE reel_scripts_new RENAME TO reel_scripts;
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_reel_frameworks(conn: sqlite3.Connection, video_format: str | None = None) -> list[dict]:
    """video_format filters to 'talking_head' or 'beat_edit' rows. If the filtered
    pool is empty, falls back to the unfiltered pool — a format mismatch is better
    than blocking generation entirely (the tier's prompt template already constrains
    output shape regardless of which framework gets picked for pacing/scene-count)."""
    if video_format:
        rows = conn.execute(
            "SELECT * FROM reel_frameworks WHERE COALESCE(video_format, 'talking_head') = ? "
            "ORDER BY created_at DESC",
            (video_format,),
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]
    rows = conn.execute(
        "SELECT * FROM reel_frameworks ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

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


def score_frameworks(
    story: dict,
    frameworks: list[dict],
    idea_prompt: str | None,
) -> list[dict]:
    tags = set(t.lower() for t in _parse_json_list(story.get("thematic_tags", [])))
    idea_lower = (idea_prompt or "").lower()
    scored = []
    for fw in frameworks:
        topics = set(t.lower() for t in _parse_json_list(fw.get("fits_topics", [])))
        score = len(topics & tags)
        if idea_lower and any(t in idea_lower for t in topics):
            score += 1
        scored.append({**fw, "_score": score})
    return sorted(scored, key=lambda x: x["_score"], reverse=True)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def _format_framework(fw: dict) -> str:
    structure = fw.get("structure_json", "[]")
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except Exception:
            pass
    structure_str = json.dumps(structure, indent=2) if isinstance(structure, list) else str(structure)

    if fw.get("video_format") == "beat_edit":
        return (
            f"Duration target: {fw.get('duration_sec', 0.0):.1f}s\n"
            f"Hook type (visual, from a DIFFERENT reel — copy the SHAPE, never the subject): {fw.get('hook_type', '')}\n"
            f"Tone: {fw.get('tone', '')}\n"
            f"Scene count: {fw.get('scene_count', '')}\n"
            f"Visual grammar (color system / shot pattern — from a DIFFERENT reel, shape only): {fw.get('visual_notes', '')}\n"
            f"Beat list (SHAPE template — its on-screen text is from a DIFFERENT story; never reuse it as content):\n{structure_str}"
        )

    return (
        f"Duration target: {fw.get('duration_sec', 0.0):.1f}s\n"
        f"Hook type: {fw.get('hook_type', '')}\n"
        f"Hook verbal (EXAMPLE from an UNRELATED topic — copy the SHAPE, never the subject): {fw.get('hook_verbal', '')}\n"
        f"Hook silence (pre-speech): {fw.get('hook_silence_sec', 0.0):.2f}s\n"
        f"Pacing: {fw.get('pacing', '')}\n"
        f"Tone: {fw.get('tone', '')}\n"
        f"CTA type: {fw.get('cta_type', '')}\n"
        f"CTA verbal (EXAMPLE from an UNRELATED topic — shape only, never the subject): {fw.get('cta_verbal', '')}\n"
        f"Scene count: {fw.get('scene_count', '')}\n"
        f"Structure (SHAPE template — its example topics/tools are from a DIFFERENT story; never reuse them as content):\n{structure_str}"
    )


def build_freeform_script_prompt(
    idea_prompt: str,
    framework: dict,
    tier: str = "scripted-headshot",
) -> str:
    template_path = TIER_TEMPLATES.get(tier, TIER_TEMPLATES["scripted-headshot"])
    template = template_path.read_text(encoding="utf-8")
    voice_block = VOICE_BLOCK_PATH.read_text(encoding="utf-8")
    return llm_client.inject(
        template,
        VOICE_BLOCK=voice_block,
        FRAMEWORK=_format_framework(framework),
        IDEA=idea_prompt,
    )


# ---------------------------------------------------------------------------
# Generate + save
# ---------------------------------------------------------------------------

def clean_script_output(text: str) -> str:
    """Strip scene headers and VOICEOVER labels from LLM output."""
    import re
    # Strip a wrapping markdown code fence (```...```), if the model added one
    text = text.strip()
    fence_match = re.match(r"^```[^\n]*\n(.*)\n```$", text, flags=re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    # Remove lines like "SCENE 3 (4.2s–6.0s):" or "**SCENE 3 (4.2s–6.0s):**"
    text = re.sub(r"\*{0,2}SCENE\s+\d+[^:\n]*:\*{0,2}\s*\n?", "", text, flags=re.IGNORECASE)
    # Remove "VOICEOVER:" prefix (with optional bold markers)
    text = re.sub(r"\*{0,2}VOICEOVER:\*{0,2}\s*", "", text, flags=re.IGNORECASE)
    # Remove "---" dividers
    text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_script(prompt: str, cfg: dict) -> tuple[str, str]:
    script, model_used = llm_client.complete(prompt, section="script_writer")
    return clean_script_output(script), model_used


def save_script(
    conn: sqlite3.Connection,
    story_node_id: int,
    framework_id: str,
    idea_prompt: str | None,
    script: str,
    model: str,
    duration_target: float,
    framework_pick_reason: str | None = None,
    tier: str | None = None,
    version: int = 1,
    parent_script_id: int | None = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO reel_scripts
            (story_node_id, framework_id, idea_prompt, generated_text, model_used,
             duration_target_sec, created_at, framework_pick_reason, tier, version, parent_script_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (story_node_id, framework_id, idea_prompt, script, model, duration_target, now,
         framework_pick_reason, tier, version, parent_script_id),
    )
    conn.commit()
    return cur.lastrowid
