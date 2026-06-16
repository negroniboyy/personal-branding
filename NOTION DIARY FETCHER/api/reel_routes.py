"""HTTP API for Instagram Reels: script generation + manual MP4 ingest."""

import json
import sqlite3
import subprocess
import sys
import threading
import tomllib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).parent.parent.parent
_FRAMEWORKS_DIR = _REPO_ROOT / "frameworks" / "instagram_frameworks"
_CONFIG_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "config.toml"
sys.path.insert(0, str(_FRAMEWORKS_DIR))
sys.path.insert(0, str(_REPO_ROOT))


def _reel_config() -> dict:
    try:
        with open(_CONFIG_PATH, "rb") as f:
            return tomllib.load(f).get("content_writer", {})
    except FileNotFoundError:
        return {}

import extract_reel
import llm_client
import script_writer
from shared.lifecycle import (
    CAPTION_PROMPT,
    get_feedback_block,
    migrate_lifecycle_columns,
    parse_package_output,
    save_package,
    update_meta,
)
from shared.logger import get_logger
from shared.md_mirror import delete_script_md, write_script_md

logger = get_logger("instagram_frameworks")

DB_PATH = Path(__file__).parent.parent / "data" / "notion_diary.db"
REFERENCES_DIR = extract_reel.REFERENCES_DIR
EXTRACT_PROMPT_PATH = extract_reel.PROMPT_PATH
SCRIPT_PROMPT_PATH = script_writer.PROMPT_PATH

_scan_lock = threading.Lock()

router = APIRouter(prefix="/reels", tags=["reels"])


class RecommendationRequestBody(BaseModel):
    idea_prompt: Optional[str] = None
    top_n: int = 20
    domain: Optional[str] = None


class GenerateRequestBody(BaseModel):
    story_node_id: Optional[str] = None
    framework_id: str
    idea_prompt: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class PatchScriptBody(BaseModel):
    generated_text: str


class MetaBody(BaseModel):
    status: Optional[str] = None
    verdict: Optional[int] = None
    verdict_note: Optional[str] = None
    asana_task_gid: Optional[str] = None


class PackageBody(BaseModel):
    model: Optional[str] = None


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# One-time schema upgrade so /meta and /package work before any generation runs.
try:
    _conn = _db()
    migrate_lifecycle_columns(_conn, "reel_scripts")
    _conn.close()
except Exception as _e:
    logger.warning("lifecycle migration skipped: %s", _e)


@router.get("/frameworks")
def list_frameworks():
    conn = _db()
    try:
        return script_writer.load_reel_frameworks(conn)
    finally:
        conn.close()


@router.post("/recommendations")
def get_recommendations(body: RecommendationRequestBody):
    cfg = _reel_config()
    min_worth = cfg.get("min_worth_score", 0.0)
    conn = _db()
    try:
        stories = script_writer.load_story_nodes(
            conn, limit=body.top_n, min_worth_score=min_worth, domain=body.domain
        )
        all_fw = script_writer.load_reel_frameworks(conn)
        if stories and all_fw:
            scored = script_writer.score_frameworks(stories[0], all_fw, body.idea_prompt)
            frameworks = scored[:body.top_n]
        else:
            frameworks = all_fw[:body.top_n]
        return {"stories": stories, "frameworks": frameworks}
    finally:
        conn.close()


@router.post("/generate")
def generate(body: GenerateRequestBody):
    conn = _db()
    try:
        fw_row = conn.execute(
            "SELECT * FROM reel_frameworks WHERE id = ?",
            (body.framework_id,),
        ).fetchone()
        if not fw_row:
            raise HTTPException(status_code=404, detail=f"reel_framework {body.framework_id!r} not found")

        framework = dict(fw_row)

        if body.story_node_id is None:
            if not body.idea_prompt:
                raise HTTPException(status_code=422, detail="idea_prompt is required when no story is selected")
            prompt = script_writer.build_freeform_script_prompt(body.idea_prompt, framework)
            story_node_id_saved = None
        else:
            story_row = conn.execute(
                "SELECT id, page_id, user_state, conflict_node, desired_outcome, "
                "the_bridge, thematic_tags, worth_score "
                "FROM story_nodes WHERE id = ?",
                (body.story_node_id,),
            ).fetchone()
            if not story_row:
                raise HTTPException(status_code=404, detail=f"story_node {body.story_node_id} not found")
            prompt_template = SCRIPT_PROMPT_PATH.read_text(encoding="utf-8")
            source_text = script_writer.get_chunks_for_story(conn, body.story_node_id)
            prompt = script_writer.build_script_prompt(dict(story_row), framework, body.idea_prompt, prompt_template, source_text=source_text)
            story_node_id_saved = body.story_node_id

        prompt += get_feedback_block(conn, "reel_scripts")
        messages = [{"role": "user", "content": prompt}]
        from openrouter.router import chat as llm_chat
        # Honor the model picked in the UI for EVERY provider. router.chat sends
        # "ollama:" ids to the local runtime and plain ids to OpenRouter, and
        # returns the model actually used — so model_used is always accurate.
        # With no model sent, it falls back to the configured task chain.
        result = llm_chat(
            "generate_reel_script", messages,
            max_tokens=2048,
            override_model=body.model or None,
        )
        text = script_writer.clean_script_output(result["content"])
        model_used = result["model"]

        script_writer.init_db(conn)
        duration_target = float(framework.get("duration_sec") or 0.0)
        script_id = script_writer.save_script(
            conn, story_node_id_saved, body.framework_id, body.idea_prompt,
            text, model_used, duration_target,
        )
        created_row = conn.execute(
            "SELECT created_at FROM reel_scripts WHERE id = ?",
            (script_id,),
        ).fetchone()
        created_at = created_row["created_at"] if created_row else None
        try:
            write_script_md({
                "id": script_id,
                "story_node_id": story_node_id_saved,
                "framework_id": body.framework_id,
                "model_used": model_used,
                "created_at": created_at,
                "generated_text": text,
            })
        except Exception as e:
            logger.warning("write_script_md failed for id=%s: %s", script_id, e)
        return {
            "script_id": script_id,
            "generated_text": text,
            "story_node_id": story_node_id_saved,
            "framework_id": body.framework_id,
            "model_used": model_used,
            "created_at": created_at,
        }
    finally:
        conn.close()


@router.post("/generate/stream")
async def generate_stream(body: GenerateRequestBody):
    from openrouter.router import stream as llm_stream

    conn = _db()
    try:
        fw_row = conn.execute(
            "SELECT * FROM reel_frameworks WHERE id = ?", (body.framework_id,)
        ).fetchone()
        if not fw_row:
            raise HTTPException(status_code=404, detail=f"reel_framework {body.framework_id!r} not found")
        framework = dict(fw_row)

        if body.story_node_id is None:
            if not body.idea_prompt:
                raise HTTPException(status_code=422, detail="idea_prompt required without story")
            prompt = script_writer.build_freeform_script_prompt(body.idea_prompt, framework)
            story_node_id_saved = None
        else:
            story_row = conn.execute(
                "SELECT id, page_id, user_state, conflict_node, desired_outcome, "
                "the_bridge, thematic_tags, worth_score FROM story_nodes WHERE id = ?",
                (body.story_node_id,),
            ).fetchone()
            if not story_row:
                raise HTTPException(status_code=404, detail=f"story_node {body.story_node_id} not found")
            prompt_template = SCRIPT_PROMPT_PATH.read_text(encoding="utf-8")
            source_text = script_writer.get_chunks_for_story(conn, body.story_node_id)
            prompt = script_writer.build_script_prompt(dict(story_row), framework, body.idea_prompt, prompt_template, source_text=source_text)
            story_node_id_saved = body.story_node_id

        prompt += get_feedback_block(conn, "reel_scripts")
        duration_target = float(framework.get("duration_sec") or 0.0)
    finally:
        conn.close()

    messages = [{"role": "user", "content": prompt}]

    async def event_generator():
        try:
            async for chunk in llm_stream(
                "generate_reel_script", messages, max_tokens=2048,
                override_model=body.model or None,
            ):
                if chunk["type"] == "done":
                    conn2 = _db()
                    try:
                        script_writer.init_db(conn2)
                        cleaned = script_writer.clean_script_output(chunk["content"])
                        chunk["content"] = cleaned
                        script_id = script_writer.save_script(
                            conn2, story_node_id_saved, body.framework_id, body.idea_prompt,
                            cleaned, chunk["model"], duration_target,
                        )
                        created_row = conn2.execute(
                            "SELECT created_at FROM reel_scripts WHERE id = ?", (script_id,)
                        ).fetchone()
                        chunk["script_id"] = script_id
                        chunk["created_at"] = created_row["created_at"] if created_row else None
                        try:
                            write_script_md({
                                "id": script_id,
                                "story_node_id": story_node_id_saved,
                                "framework_id": body.framework_id,
                                "model_used": chunk["model"],
                                "created_at": chunk["created_at"],
                                "generated_text": chunk["content"],
                            })
                        except Exception as e:
                            logger.warning("write_script_md failed for id=%s: %s", script_id, e)
                    finally:
                        conn2.close()
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/scripts")
def list_scripts(status: Optional[str] = None, limit: int = 100):
    conn = _db()
    try:
        where, params = "", []
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(limit)
        rows = conn.execute(
            "SELECT id, story_node_id, framework_id, model_used, created_at, "
            "generated_text, status, verdict, verdict_note, caption, cta, "
            "asana_task_gid, posted_at "
            f"FROM reel_scripts {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.patch("/scripts/{script_id}/meta")
def patch_script_meta(script_id: int, body: MetaBody):
    conn = _db()
    try:
        try:
            updated = update_meta(conn, "reel_scripts", script_id, body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if not updated:
            raise HTTPException(status_code=404, detail=f"reel_script {script_id} not found")
        return updated
    finally:
        conn.close()


@router.post("/scripts/{script_id}/package")
def package_script(script_id: int, body: PackageBody):
    """Generate caption + CTA for a REVIEWED script. Rejected while still queued."""
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM reel_scripts WHERE id = ?", (script_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"reel_script {script_id} not found")
        if (row["status"] or "queued") in ("queued", "killed"):
            raise HTTPException(
                status_code=409,
                detail="script must be approved (reviewed) before packaging caption/CTA",
            )
        from openrouter.router import chat as llm_chat
        result = llm_chat(
            "generate_reel_script",
            [{"role": "user", "content": CAPTION_PROMPT.format(content=row["generated_text"])}],
            max_tokens=512,
            override_model=body.model or None,
        )
        caption, cta = parse_package_output(result["content"])
        save_package(conn, "reel_scripts", script_id, caption, cta)
        return {"script_id": script_id, "caption": caption, "cta": cta, "model_used": result["model"]}
    finally:
        conn.close()


@router.get("/scripts/{script_id}")
def get_script(script_id: int):
    conn = _db()
    try:
        row = conn.execute(
            "SELECT * FROM reel_scripts WHERE id = ?",
            (script_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"reel_script {script_id} not found")
        return dict(row)
    finally:
        conn.close()


@router.patch("/scripts/{script_id}")
def patch_script(script_id: int, body: PatchScriptBody):
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM reel_scripts WHERE id = ?", (script_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"reel_script {script_id} not found")
        conn.execute(
            "UPDATE reel_scripts SET generated_text = ? WHERE id = ?",
            (body.generated_text, script_id),
        )
        conn.commit()
        updated = dict(conn.execute("SELECT * FROM reel_scripts WHERE id = ?", (script_id,)).fetchone())
        try:
            write_script_md(updated)
        except Exception as e:
            logger.warning("write_script_md failed on patch id=%s: %s", script_id, e)
        return updated
    finally:
        conn.close()


@router.delete("/scripts/{script_id}")
def delete_script(script_id: int):
    conn = _db()
    try:
        row = conn.execute("SELECT id FROM reel_scripts WHERE id = ?", (script_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"reel_script {script_id} not found")
        conn.execute("DELETE FROM reel_scripts WHERE id = ?", (script_id,))
        conn.commit()
        try:
            delete_script_md(script_id)
        except Exception as e:
            logger.warning("delete_script_md failed for id=%s: %s", script_id, e)
        return {"ok": True}
    finally:
        conn.close()


@router.post("/open-scripts-folder")
def open_scripts_folder():
    from shared.md_mirror import _load_dirs
    scripts_dir, _ = _load_dirs()
    scripts_dir.mkdir(parents=True, exist_ok=True)
    plat = sys.platform
    if plat == "darwin":
        subprocess.Popen(["open", str(scripts_dir)])
    elif plat.startswith("linux"):
        subprocess.Popen(["xdg-open", str(scripts_dir)])
    else:
        raise HTTPException(status_code=501, detail=f"open-folder not supported on {plat}")
    logger.info("opened scripts folder at %s", scripts_dir)
    return {"opened": True, "path": str(scripts_dir)}


@router.post("/open-references")
def open_references():
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    plat = sys.platform
    if plat == "darwin":
        subprocess.Popen(["open", str(REFERENCES_DIR)])
    elif plat.startswith("linux"):
        subprocess.Popen(["xdg-open", str(REFERENCES_DIR)])
    else:
        raise HTTPException(status_code=501, detail=f"open-folder not supported on {plat}")
    logger.info("opened references folder at %s", REFERENCES_DIR)
    return {"opened": True, "path": str(REFERENCES_DIR), "platform": plat}


@router.post("/scan")
def scan_references():
    if not _scan_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="scan already running")
    try:
        REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(p for p in REFERENCES_DIR.iterdir() if p.suffix.lower() == ".mp4")
        succeeded: list[dict] = []
        failed: list[dict] = []
        if not files:
            return {
                "processed": 0,
                "succeeded": succeeded,
                "failed": failed,
                "references_dir": str(REFERENCES_DIR),
            }

        cfg = llm_client.load_config("reel_extractor")
        prompt_template = EXTRACT_PROMPT_PATH.read_text(encoding="utf-8")
        conn = _db()
        try:
            extract_reel.init_db(conn)
            for filepath in files:
                logger.info("scan: processing %s", filepath.name)
                framework_id, status = extract_reel.process_file(
                    filepath, cfg, prompt_template, conn
                )
                if status == "OK":
                    try:
                        filepath.unlink()
                        deleted = True
                    except OSError as e:
                        logger.warning("scan: could not delete %s: %s", filepath.name, e)
                        deleted = False
                    succeeded.append({"file": filepath.name, "framework_id": framework_id, "deleted": deleted})
                elif status.startswith("OK"):
                    succeeded.append({"file": filepath.name, "framework_id": framework_id, "deleted": False})
                else:
                    failed.append({"file": filepath.name, "status": status})
        finally:
            conn.close()

        logger.info(
            "scan complete: %d processed, %d succeeded, %d failed",
            len(files), len(succeeded), len(failed),
        )
        return {
            "processed": len(files),
            "succeeded": succeeded,
            "failed": failed,
            "references_dir": str(REFERENCES_DIR),
        }
    finally:
        _scan_lock.release()
