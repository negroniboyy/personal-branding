#!/usr/bin/env python3
"""
Generate Instagram Reel video scripts by matching story_nodes to reel frameworks.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import llm_client
import yaml
from shared.logger import get_logger

logger = get_logger("instagram_frameworks")

SCRIPT_DIR  = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
PROMPT_PATH = PROMPTS_DIR / "script_writer.txt"
IDEA_PROMPT_PATH = PROMPTS_DIR / "script_writer_idea.txt"
VOICE_BLOCK_PATH = SCRIPT_DIR.parent.parent / "brandguide" / "voice_dna_block.txt"

DB_PATH = Path(__file__).parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"
if not DB_PATH.exists():
    DB_PATH = Path(__file__).parent.parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"


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

ROMANTIC_TAGS = {
    "relationship", "relationships", "dating", "romance", "romantic",
    "love", "partner", "marriage", "breakup", "heartbreak",
}


def load_story_nodes(
    conn: sqlite3.Connection,
    limit: int,
    min_worth_score: float = 0.0,
    domain: str | None = None,
    exclude_used_in: str | None = None,
) -> list[dict]:
    filters = ["worth_score >= ?"]
    params: list = [min_worth_score]

    if domain:
        filters.append("thematic_tags LIKE ?")
        params.append(f"%{domain}%")

    # Rotation: skip story nodes that already produced a draft in the given
    # table (e.g. "reel_scripts") so each batch reaches fresh notes instead of
    # re-mining the same top-scored ones every run. CAST guards int/str id-type
    # drift between story_nodes.id and <table>.story_node_id.
    if exclude_used_in:
        filters.append(
            f"CAST(id AS TEXT) NOT IN "
            f"(SELECT CAST(story_node_id AS TEXT) FROM {exclude_used_in} "
            f"WHERE story_node_id IS NOT NULL)"
        )

    # Exclude story nodes whose primary subject is romantic/relationship content
    for tag in ROMANTIC_TAGS:
        filters.append("(thematic_tags NOT LIKE ? OR thematic_tags IS NULL)")
        params.append(f'%"{tag}"%')

    where = " AND ".join(filters)
    params.append(limit * 3)  # fetch extra to allow post-filter

    rows = conn.execute(
        f"""
        SELECT id, page_id, user_state, conflict_node, desired_outcome,
               the_bridge, thematic_tags, worth_score
        FROM story_nodes
        WHERE {where}
        ORDER BY worth_score DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    # Secondary filter: exclude if user_state text is dominantly about relationships
    _romantic_words = {"relationship", "romantic", "partner", "dating", "girlfriend", "boyfriend"}
    results = []
    for r in rows:
        state = (r["user_state"] or "").lower()
        word_hits = sum(1 for w in _romantic_words if w in state)
        if word_hits <= 1:  # allow incidental mentions
            results.append(dict(r))
        if len(results) >= limit:
            break

    return results


def load_reel_frameworks(conn: sqlite3.Connection) -> list[dict]:
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


def count_conflict_nodes(story: dict) -> int:
    cn = story.get("conflict_node", "") or ""
    parts = [p.strip() for p in cn.replace(";", ",").split(",") if p.strip()]
    return max(1, len(parts))


# ---------------------------------------------------------------------------
# Recommendation view
# ---------------------------------------------------------------------------

def build_recommendation_view(
    stories: list[dict],
    frameworks_scored: list[dict],
    short_threshold: float,
) -> str:
    lines = ["\n=== STORY RECOMMENDATIONS (top 5 by worth_score) ==="]
    for i, s in enumerate(stories[:5], 1):
        preview = (s.get("user_state") or s.get("conflict_node") or "")[:60]
        lines.append(f"  [{i}] (id={s['id']}, worth={s.get('worth_score', 0):.1f}) {preview}")

    lines.append("\n=== FRAMEWORK RECOMMENDATIONS (top 3 by topic overlap) ===")
    for i, fw in enumerate(frameworks_scored[:3], 1):
        dur = fw.get("duration_sec", 0.0)
        warn = ""
        if dur < short_threshold and any(count_conflict_nodes(s) > 2 for s in stories[:5]):
            warn = " ⚠ short reel — may not fit complex stories"
        lines.append(
            f"  [{i}] (id={fw['id']}, dur={dur:.1f}s, hook={fw.get('hook_type','')}, "
            f"pacing={fw.get('pacing','')}) score={fw['_score']}{warn}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pick
# ---------------------------------------------------------------------------

def pick(
    stories: list[dict],
    frameworks: list[dict],
    story_id_arg: int | None,
    framework_id_arg: str | None,
    non_interactive: bool,
) -> tuple[dict, dict]:
    if story_id_arg is not None:
        story_matches = [s for s in stories if s["id"] == str(story_id_arg)]
        if not story_matches:
            raise ValueError(f"story_node id={story_id_arg} not found")
        story = story_matches[0]
    elif non_interactive:
        story = stories[0]
    else:
        choice = input(f"\nSelect story [1–{min(5, len(stories))}] (Enter = 1): ").strip()
        idx = (int(choice) - 1) if choice.isdigit() else 0
        idx = max(0, min(idx, len(stories) - 1))
        story = stories[idx]

    if framework_id_arg is not None:
        fw_matches = [f for f in frameworks if f["id"] == framework_id_arg]
        if not fw_matches:
            raise ValueError(f"reel_framework id={framework_id_arg!r} not found")
        framework = fw_matches[0]
    elif non_interactive:
        framework = frameworks[0]
    else:
        choice = input(f"Select framework [1–{min(3, len(frameworks))}] (Enter = 1): ").strip()
        idx = (int(choice) - 1) if choice.isdigit() else 0
        idx = max(0, min(idx, len(frameworks) - 1))
        framework = frameworks[idx]

    return story, framework


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def _format_story(story: dict) -> str:
    tags = ", ".join(_parse_json_list(story.get("thematic_tags", [])))
    return (
        f"User state (pain): {story.get('user_state', '')}\n"
        f"Conflict node: {story.get('conflict_node', '')}\n"
        f"Desired outcome: {story.get('desired_outcome', '')}\n"
        f"The bridge (transformation): {story.get('the_bridge', '')}\n"
        f"Thematic tags: {tags}"
    )


def _format_framework(fw: dict) -> str:
    structure = fw.get("structure_json", "[]")
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except Exception:
            pass
    structure_str = json.dumps(structure, indent=2) if isinstance(structure, list) else str(structure)
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


def get_chunks_for_story(conn: sqlite3.Connection, story_id: str, max_chars: int = 4000) -> str:
    """Raw verbatim diary text behind a story node, joined and capped.

    This is the real source material the script must be built from. The reel
    pipeline historically only passed the distilled story_node fields, which
    are too abstract — the model then borrowed concrete details from the
    framework's example instead. This reconnects the script to the diary.
    """
    rows = conn.execute(
        """
        SELECT c.chunk_text FROM chunks c
        JOIN story_nodes sn ON sn.page_id = c.page_id
        WHERE sn.id = ?
        ORDER BY c.chunk_index
        """,
        (story_id,),
    ).fetchall()
    texts = [r["chunk_text"] for r in rows if r["chunk_text"]]
    return "\n\n".join(texts)[:max_chars]


def _format_chunks(source_text: str) -> str:
    text = (source_text or "").strip()
    if not text:
        return (
            "(no verbatim diary text available — rely on the distilled fields above "
            "and DO NOT invent concrete specifics, names, tools, or events)"
        )
    return text


def build_script_prompt(
    story: dict,
    framework: dict,
    idea_prompt: str | None,
    prompt_template: str,
    source_text: str = "",
) -> str:
    idea_section = (
        f"PRIMARY ANGLE — lead with this, use the story only as factual backing:\n{idea_prompt}"
        if idea_prompt
        else "(none provided — improvise from story)"
    )
    return llm_client.inject(
        prompt_template,
        STORY=_format_story(story),
        SOURCE=_format_chunks(source_text),
        FRAMEWORK=_format_framework(framework),
        IDEA=idea_section,
    )


def build_freeform_script_prompt(
    idea_prompt: str,
    framework: dict,
) -> str:
    template = IDEA_PROMPT_PATH.read_text(encoding="utf-8")
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
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO reel_scripts
            (story_node_id, framework_id, idea_prompt, generated_text, model_used,
             duration_target_sec, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (story_node_id, framework_id, idea_prompt, script, model, duration_target, now),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(
    idea_prompt: str | None,
    story_id: int | None,
    framework_id: str | None,
    dry_run: bool,
    cfg: dict,
) -> None:
    non_interactive = dry_run or (story_id is not None and framework_id is not None)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)  # creates reel_scripts (and reel_frameworks if missing)
    # reel_frameworks table must exist (created by extract_reel.py init_db); ensure it here too
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reel_frameworks (
            id TEXT PRIMARY KEY, creator TEXT, channel TEXT, source_file TEXT,
            duration_sec REAL, scene_count INTEGER, scene_intervals TEXT,
            hook_type TEXT, hook_verbal TEXT, hook_silence_sec REAL,
            structure_json TEXT, pacing TEXT, tone TEXT,
            cta_type TEXT, cta_verbal TEXT, fits_topics TEXT,
            transcript_json TEXT, transcript_text TEXT,
            visual_notes TEXT DEFAULT '', performance_notes TEXT DEFAULT '',
            yaml_path TEXT, created_at TEXT
        )
    """)
    conn.commit()

    stories    = load_story_nodes(conn, cfg["top_n_stories"])
    frameworks = load_reel_frameworks(conn)

    if not stories:
        logger.error("No story_nodes found in DB")
        conn.close()
        sys.exit(1)
    if not frameworks:
        logger.error("No reel_frameworks found in DB — run extract_reel.py first")
        conn.close()
        sys.exit(1)

    anchor_story = next((s for s in stories if story_id and s["id"] == str(story_id)), stories[0])
    frameworks_scored = score_frameworks(anchor_story, frameworks, idea_prompt)

    if not (story_id and framework_id):
        print(build_recommendation_view(stories, frameworks_scored, cfg["short_reel_threshold_sec"]))

    story, framework = pick(
        stories, frameworks_scored,
        story_id, framework_id,
        non_interactive,
    )

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = build_script_prompt(story, framework, idea_prompt, prompt_template)

    if dry_run:
        print("\n=== DRY RUN — SCRIPT PROMPT ===\n")
        print(prompt)
        conn.close()
        return

    print(f"\nGenerating script (story={story['id']}, framework={framework['id']}) ...", flush=True)
    script, model = generate_script(prompt, cfg)

    duration_target = float(framework.get("duration_sec") or 0.0)
    script_id = save_script(conn, story["id"], framework["id"], idea_prompt,
                             script, model, duration_target)
    conn.close()

    print(f"\n--- reel_scripts.id={script_id} | story={story['id']} | framework={framework['id']} ---\n")
    print(script)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Instagram Reel scripts")
    parser.add_argument("--idea",         default=None, help="Optional video idea / framing hint")
    parser.add_argument("--story-id",     type=int,     default=None, help="story_node id (skip interactive pick)")
    parser.add_argument("--framework-id", default=None, help="reel_framework id (skip interactive pick)")
    parser.add_argument("--dry-run",      action="store_true", help="Print prompt; no Ollama, no DB writes")
    args = parser.parse_args()

    cfg = llm_client.load_config("script_writer")
    run(args.idea, args.story_id, args.framework_id, args.dry_run, cfg)
