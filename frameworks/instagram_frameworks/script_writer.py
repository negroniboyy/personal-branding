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
from shared.logger import get_logger

logger = get_logger("instagram_frameworks")

SCRIPT_DIR  = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
PROMPT_PATH = PROMPTS_DIR / "script_writer.txt"

DB_PATH = Path(__file__).parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"
if not DB_PATH.exists():
    DB_PATH = Path(__file__).parent.parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

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
    conn.commit()


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_story_nodes(conn: sqlite3.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, page_id, user_state, conflict_node, desired_outcome,
               the_bridge, thematic_tags, worth_score
        FROM story_nodes
        ORDER BY worth_score DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


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
        f"Hook verbal: {fw.get('hook_verbal', '')}\n"
        f"Hook silence (pre-speech): {fw.get('hook_silence_sec', 0.0):.2f}s\n"
        f"Pacing: {fw.get('pacing', '')}\n"
        f"Tone: {fw.get('tone', '')}\n"
        f"CTA type: {fw.get('cta_type', '')}\n"
        f"CTA verbal example: {fw.get('cta_verbal', '')}\n"
        f"Scene count: {fw.get('scene_count', '')}\n"
        f"Structure:\n{structure_str}"
    )


def build_script_prompt(
    story: dict,
    framework: dict,
    idea_prompt: str | None,
    prompt_template: str,
) -> str:
    return llm_client.inject(
        prompt_template,
        STORY=_format_story(story),
        FRAMEWORK=_format_framework(framework),
        IDEA=idea_prompt or "(none provided — improvise from story)",
    )


# ---------------------------------------------------------------------------
# Generate + save
# ---------------------------------------------------------------------------

def generate_script(prompt: str, cfg: dict) -> tuple[str, str]:
    script = llm_client.complete(prompt, section="script_writer")
    return script, cfg["ollama_model"]


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
