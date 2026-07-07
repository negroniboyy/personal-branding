#!/usr/bin/env python3
"""
Batch reel script generator.
Usage:
    python3 batch_generate.py
    python3 batch_generate.py --stories 5 --frameworks 2

Picks top N story_nodes by worth_score, matches each with top M frameworks
by tag overlap, generates a script for every (story, framework) pair.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# ── path setup ───────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.resolve()
FW_DIR     = ROOT / "frameworks" / "instagram_frameworks"
NDF_DIR    = ROOT / "NOTION DIARY FETCHER"
SHARED_DIR = ROOT / "shared"

for p in [str(FW_DIR), str(NDF_DIR), str(SHARED_DIR), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# tomllib backport for Python < 3.11
try:
    import tomllib  # noqa: F401
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
        sys.modules["tomllib"] = tomllib
    except ModuleNotFoundError:
        sys.exit("Missing dependency: pip install tomli")

# Ensure OPENROUTER_API_KEY is loaded before any module that needs it.
# Robust to the root `uv run` env not having python-dotenv installed
# (the nightly runs this from repo root): prefer dotenv, fall back to a
# manual parse of NOTION DIARY FETCHER/.env so the scheduled task can't crash.
import os  # noqa: E402


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(NDF_DIR / ".env")
        return
    except ModuleNotFoundError:
        pass
    env_path = NDF_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()

import llm_client          # noqa: E402  (instagram_frameworks/llm_client.py)
import script_writer as sw  # noqa: E402


# ── matching ──────────────────────────────────────────────────────────────────

def top_frameworks_for_story(story: dict, frameworks: list[dict], n: int) -> list[dict]:
    scored = sw.score_frameworks(story, frameworks, idea_prompt=None)
    return scored[:n]


# ── main ─────────────────────────────────────────────────────────────────────

def run(n_stories: int, n_frameworks: int, dry_run: bool) -> None:
    db_path = sw.DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sw.init_db(conn)

    # Rotation: prefer notes that haven't been scripted yet. If every eligible
    # note has already been used, fall back to the unfiltered top-N so the
    # nightly run still produces something rather than going empty.
    stories    = sw.load_story_nodes(conn, limit=n_stories, exclude_used_in="reel_scripts")
    if not stories:
        print("All top story_nodes already scripted — falling back to top-N (no rotation).")
        stories = sw.load_story_nodes(conn, limit=n_stories)
    frameworks = sw.load_reel_frameworks(conn)

    if not stories:
        sys.exit("No story_nodes in DB.")
    if not frameworks:
        sys.exit("No reel_frameworks in DB — run extract_reel.py first.")

    cfg             = llm_client.load_config("script_writer")
    prompt_template = sw.PROMPT_PATH.read_text(encoding="utf-8")

    pairs = []
    for story in stories:
        top_fws = top_frameworks_for_story(story, frameworks, n_frameworks)
        for fw in top_fws:
            pairs.append((story, fw))

    print(f"\nBatch: {len(stories)} stories × {n_frameworks} frameworks = {len(pairs)} scripts\n")

    for i, (story, fw) in enumerate(pairs, 1):
        tag = f"[{i}/{len(pairs)}] story={story['id']} × fw={fw['id']}"
        print(f"\n{'─'*60}\n{tag}\n{'─'*60}")
        print(f"  Story : {(story.get('user_state') or '')[:80]}")
        print(f"  Hook  : {fw.get('hook_type')} | {fw.get('pacing')} | {fw.get('tone')} | {fw.get('duration_sec')}s")

        if dry_run:
            print("  [dry-run — skipping generation]")
            continue

        try:
            source    = sw.get_chunks_for_story(conn, story["id"])
            prompt    = sw.build_script_prompt(story, fw, None, prompt_template, source_text=source)
            script, model = sw.generate_script(prompt, cfg)
            # Thinking models occasionally spend the whole token budget reasoning
            # and return empty content — retry once rather than saving a blank draft.
            if len(script.strip()) < 40:
                print("  ⚠ empty output — retrying once")
                script, model = sw.generate_script(prompt, cfg)
            if len(script.strip()) < 40:
                print("  ✗ SKIPPED: still empty after retry")
                continue
            duration  = float(fw.get("duration_sec") or 0.0)
            script_id = sw.save_script(
                conn, story["id"], fw["id"], None, script, model, duration
            )
            print(f"\n  ✓ saved → reel_scripts.id={script_id}\n")
            print(script)
        except Exception as e:
            print(f"  ✗ FAILED: {e}")

    conn.close()
    if not dry_run:
        print(f"\n{'='*60}\nDone. {len(pairs)} scripts attempted.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch reel script generator")
    parser.add_argument("--stories",    type=int, default=2, help="Number of top story_nodes to use")
    parser.add_argument("--frameworks", type=int, default=2, help="Frameworks per story")
    parser.add_argument("--dry-run",    action="store_true",  help="Print pairs only, no generation")
    args = parser.parse_args()

    run(args.stories, args.frameworks, args.dry_run)
