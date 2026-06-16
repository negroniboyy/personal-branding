#!/usr/bin/env python3
"""
One story node -> ALL Instagram reel frameworks.

Reuses the existing system pipeline (script_writer + llm_client + openrouter
router + prompts/script_writer.txt + config). The only thing it changes vs.
the stock CLI is: it loads a story by its TEXT id directly (the stock
--story-id is typed int and cannot accept ids like 'sn_...' / 'seed-...'),
and it loops every framework instead of picking one.

Usage:
    python3 gen_one_node.py --story-id sn_3fe9a0ad2290
    python3 gen_one_node.py --story-id sn_3fe9a0ad2290 --dry-run   # prompts only, no API, no DB
    python3 gen_one_node.py --story-id sn_3fe9a0ad2290 --no-save    # call API but don't write DB
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# ── path setup (mirror batch_generate.py) ─────────────────────────────────────
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
    import tomli as tomllib  # type: ignore
    sys.modules["tomllib"] = tomllib

from dotenv import load_dotenv  # noqa: E402
load_dotenv(NDF_DIR / ".env")

import llm_client          # noqa: E402
import script_writer as sw  # noqa: E402

STORY_COLS = ("id, page_id, user_state, conflict_node, desired_outcome, "
              "the_bridge, thematic_tags, worth_score")


def load_story_by_id(conn, story_id):
    row = conn.execute(
        f"SELECT {STORY_COLS} FROM story_nodes WHERE id = ?", (story_id,)
    ).fetchone()
    if row is None:
        sys.exit(f"story_node id={story_id!r} not found")
    return dict(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story-id", required=True)
    ap.add_argument("--dry-run", action="store_true", help="build prompts only; no API, no DB")
    ap.add_argument("--no-save", action="store_true", help="call API but do not write to reel_scripts")
    ap.add_argument("--out", default=None, help="append each result to this JSON list path")
    ap.add_argument("--framework-index", type=int, default=None,
                    help="run only the Nth framework (0-based); enables one-per-call mode")
    args = ap.parse_args()

    conn = sqlite3.connect(sw.DB_PATH)
    conn.row_factory = sqlite3.Row
    sw.init_db(conn)

    story      = load_story_by_id(conn, args.story_id)
    frameworks = sw.load_reel_frameworks(conn)
    cfg        = llm_client.load_config("script_writer")
    template   = sw.PROMPT_PATH.read_text(encoding="utf-8")

    if args.framework_index is not None:
        frameworks = [frameworks[args.framework_index]]

    print(f"Story  : {story['id']}  (worth={story.get('worth_score')})", flush=True)
    print(f"Frameworks this run: {len(frameworks)}\n", flush=True)

    results = []
    for i, fw in enumerate(frameworks, 1):
        prompt = sw.build_script_prompt(story, fw, None, template)
        head = (f"[{i}/{len(frameworks)}] fw={fw['id']} | hook={fw.get('hook_type')} "
                f"| pacing={fw.get('pacing')} | tone={fw.get('tone')} | {fw.get('duration_sec')}s")
        print("─" * 70)
        print(head)

        if args.dry_run:
            print(f"  prompt_chars={len(prompt)}  scenes={fw.get('scene_count')}")
            results.append({"framework_id": fw["id"], "prompt_chars": len(prompt),
                            "hook_type": fw.get("hook_type"), "duration_sec": fw.get("duration_sec")})
            continue

        try:
            script, model = sw.generate_script(prompt, cfg)
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            results.append({"framework_id": fw["id"], "error": str(e)})
            continue

        dur = float(fw.get("duration_sec") or 0.0)
        script_id = None
        if not args.no_save:
            script_id = sw.save_script(conn, story["id"], fw["id"], None, script, model, dur)
        print(f"  ✓ model={model} | reel_scripts.id={script_id}")
        results.append({
            "framework_id": fw["id"], "hook_type": fw.get("hook_type"),
            "pacing": fw.get("pacing"), "tone": fw.get("tone"),
            "duration_sec": fw.get("duration_sec"), "model": model,
            "reel_script_id": script_id, "script": script,
        })

    conn.close()

    if args.out:
        p = Path(args.out)
        existing = []
        if p.exists():
            try:
                existing = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        existing.extend(results)
        p.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nAppended {len(results)} → {args.out} (total {len(existing)})", flush=True)

    print(f"Done. {len(results)} frameworks processed.", flush=True)


if __name__ == "__main__":
    main()
