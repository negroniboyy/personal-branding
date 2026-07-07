"""Job handlers — thin wrappers around existing generation/extraction logic,
registered with jobs.queue so they run on the background worker instead of
blocking a request. generate_linkedin_draft and generate_reel_script are
shared by both the idea-linked flow (Ideas tab) and the one-off flow
(Writer/Reels tabs) — idea_id is optional in the payload.
"""

import sqlite3
import sys
from pathlib import Path

from content_writer.models import GenerateRequest
from content_writer.service import generate_draft as _cw_generate
from frameworks import picker
from ideas import repository as ideas_repository
from notion_ideas import sync as notion_sync

from . import queue as jobs_queue

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INSTAGRAM_FW_DIR = _REPO_ROOT / "frameworks" / "instagram_frameworks"
if str(_INSTAGRAM_FW_DIR) not in sys.path:
    sys.path.insert(0, str(_INSTAGRAM_FW_DIR))

import extract_reel  # noqa: E402 — depends on the sys.path insert above
import llm_client  # noqa: E402
import script_writer  # noqa: E402

DB_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _handle_generate_linkedin(payload: dict) -> dict:
    idea_id = payload.get("idea_id")
    idea_prompt = payload["idea_prompt"]
    framework_id = payload.get("framework_id")
    model = payload.get("model")

    conn = _db()
    try:
        reason = None
        if not framework_id:
            framework_id, reason = picker.pick_framework(conn, "linkedin", idea_prompt)

        req = GenerateRequest(
            framework_id=framework_id,
            idea_prompt=idea_prompt,
            model=model,  # None -> router uses config/openrouter_models.yaml cascade
        )
        result = _cw_generate(conn, req, framework_pick_reason=reason)
        if idea_id:
            ideas_repository.link_draft(conn, result.draft_id, idea_id)
            jobs_queue.enqueue("push_notion_status", {"idea_id": idea_id})

        return {
            "id": result.draft_id,
            "channel": "linkedin",
            "generated_text": result.generated_text,
            "framework_id": str(result.framework_id),
            "framework_pick_reason": result.framework_pick_reason,
            "model_used": result.model_used,
        }
    finally:
        conn.close()


def _handle_generate_reel(payload: dict) -> dict:
    idea_id = payload.get("idea_id")
    idea_prompt = payload["idea_prompt"]
    framework_id = payload.get("framework_id")
    model = payload.get("model")
    tier = payload.get("tier", "scripted-headshot")

    video_format = "beat_edit" if tier == "beat-edit" else "talking_head"

    conn = _db()
    try:
        reason = None
        if not framework_id:
            framework_id, reason = picker.pick_framework(conn, "reel", idea_prompt, video_format=video_format)

        fw_row = conn.execute("SELECT * FROM reel_frameworks WHERE id = ?", (framework_id,)).fetchone()
        if not fw_row:
            raise ValueError(f"reel_framework {framework_id!r} not found")
        framework = dict(fw_row)

        prompt = script_writer.build_freeform_script_prompt(idea_prompt, framework, tier=tier)
        from shared.lifecycle import get_feedback_block
        prompt += get_feedback_block(conn, "reel_scripts")

        from openrouter.router import chat as llm_chat
        result = llm_chat(
            "generate_reel_script", [{"role": "user", "content": prompt}],
            max_tokens=2048, override_model=model or None,
        )
        text = script_writer.clean_script_output(result["content"])
        model_used = result["model"]

        script_writer.init_db(conn)
        duration_target = float(framework.get("duration_sec") or 0.0)

        version, parent_script_id = 1, None
        if idea_id:
            prior = conn.execute(
                "SELECT id, MAX(version) AS v FROM reel_scripts WHERE idea_id = ?", (idea_id,)
            ).fetchone()
            if prior and prior["v"]:
                version = prior["v"] + 1
                parent_script_id = prior["id"]

        script_id = script_writer.save_script(
            conn, None, framework_id, idea_prompt, text, model_used, duration_target,
            framework_pick_reason=reason, tier=tier, version=version, parent_script_id=parent_script_id,
        )
        if idea_id:
            ideas_repository.link_reel(conn, script_id, idea_id)
            jobs_queue.enqueue("push_notion_status", {"idea_id": idea_id})

        created_row = conn.execute(
            "SELECT created_at FROM reel_scripts WHERE id = ?", (script_id,)
        ).fetchone()
        created_at = created_row["created_at"] if created_row else None

        try:
            from shared.md_mirror import write_script_md
            write_script_md({
                "id": script_id,
                "story_node_id": None,
                "framework_id": framework_id,
                "model_used": model_used,
                "created_at": created_at,
                "generated_text": text,
            })
        except Exception:
            pass

        return {
            "id": script_id,
            "channel": "reel",
            "generated_text": text,
            "framework_id": framework_id,
            "framework_pick_reason": reason,
            "model_used": model_used,
            "created_at": created_at,
            "tier": tier,
            "version": version,
            "parent_script_id": parent_script_id,
        }
    finally:
        conn.close()


def _handle_scan_reference_file(payload: dict) -> dict:
    file_path = Path(payload["file_path"])
    if not file_path.exists():
        raise ValueError(f"reference file not found: {file_path}")

    cfg = llm_client.load_config("reel_extractor")
    prompt_template = extract_reel.PROMPT_PATH.read_text(encoding="utf-8")

    conn = _db()
    try:
        extract_reel.init_db(conn)
        framework_id, status = extract_reel.process_file(file_path, cfg, prompt_template, conn)
    finally:
        conn.close()

    if status == "OK" or status.startswith("OK"):
        deleted = False
        if status == "OK":
            try:
                file_path.unlink()
                deleted = True
            except OSError:
                pass
        return {"file": file_path.name, "framework_id": framework_id, "status": status, "deleted": deleted}

    raise RuntimeError(f"extraction failed for {file_path.name}: {status}")


def _handle_scan_beat_edit_reference_file(payload: dict) -> dict:
    file_path = Path(payload["file_path"])
    if not file_path.exists():
        raise ValueError(f"reference file not found: {file_path}")

    cfg = llm_client.load_config("reel_extractor")
    vision_cfg = llm_client.load_config("reel_extractor.vision")
    prompt_template = extract_reel.BEAT_PROMPT_PATH.read_text(encoding="utf-8")

    conn = _db()
    try:
        extract_reel.init_db(conn)
        framework_id, status = extract_reel.process_beat_edit_file(
            file_path, cfg, vision_cfg, prompt_template, conn
        )
    finally:
        conn.close()

    if status == "OK" or status.startswith("OK"):
        deleted = False
        if status == "OK":
            try:
                file_path.unlink()
                deleted = True
            except OSError:
                pass
        return {"file": file_path.name, "framework_id": framework_id, "status": status, "deleted": deleted}

    raise RuntimeError(f"beat-edit extraction failed for {file_path.name}: {status}")


def _handle_sync_notion_ideas(payload: dict) -> dict:
    conn = _db()
    try:
        return notion_sync.pull_ideas(conn)
    finally:
        conn.close()


def _handle_push_notion_status(payload: dict) -> dict:
    idea_id = payload["idea_id"]
    conn = _db()
    try:
        return notion_sync.push_status(conn, idea_id)
    finally:
        conn.close()


jobs_queue.register("generate_linkedin_draft", _handle_generate_linkedin)
jobs_queue.register("generate_reel_script", _handle_generate_reel)
jobs_queue.register("scan_reference_file", _handle_scan_reference_file)
jobs_queue.register("scan_beat_edit_reference_file", _handle_scan_beat_edit_reference_file)
jobs_queue.register("sync_notion_ideas", _handle_sync_notion_ideas)
jobs_queue.register("push_notion_status", _handle_push_notion_status)
