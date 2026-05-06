"""HTTP API for Instagram Reels: script generation + manual MP4 ingest."""

import sqlite3
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).parent.parent.parent
_FRAMEWORKS_DIR = _REPO_ROOT / "frameworks" / "instagram_frameworks"
sys.path.insert(0, str(_FRAMEWORKS_DIR))

import extract_reel
import llm_client
import script_writer
from shared.logger import get_logger

logger = get_logger("instagram_frameworks")

DB_PATH = Path(__file__).parent.parent / "data" / "notion_diary.db"
REFERENCES_DIR = extract_reel.REFERENCES_DIR
EXTRACT_PROMPT_PATH = extract_reel.PROMPT_PATH
SCRIPT_PROMPT_PATH = script_writer.PROMPT_PATH

_scan_lock = threading.Lock()

router = APIRouter(prefix="/reels", tags=["reels"])


class RecommendationRequestBody(BaseModel):
    idea_prompt: Optional[str] = None
    top_n: int = 5


class GenerateRequestBody(BaseModel):
    story_node_id: str
    framework_id: str
    idea_prompt: Optional[str] = None


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/frameworks")
def list_frameworks():
    conn = _db()
    try:
        return script_writer.load_reel_frameworks(conn)
    finally:
        conn.close()


@router.post("/recommendations")
def get_recommendations(body: RecommendationRequestBody):
    conn = _db()
    try:
        stories = script_writer.load_story_nodes(conn, limit=body.top_n)
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
        story_row = conn.execute(
            "SELECT id, page_id, user_state, conflict_node, desired_outcome, "
            "the_bridge, thematic_tags, worth_score "
            "FROM story_nodes WHERE id = ?",
            (body.story_node_id,),
        ).fetchone()
        if not story_row:
            raise HTTPException(status_code=404, detail=f"story_node {body.story_node_id} not found")

        fw_row = conn.execute(
            "SELECT * FROM reel_frameworks WHERE id = ?",
            (body.framework_id,),
        ).fetchone()
        if not fw_row:
            raise HTTPException(status_code=404, detail=f"reel_framework {body.framework_id!r} not found")

        story = dict(story_row)
        framework = dict(fw_row)

        prompt_template = SCRIPT_PROMPT_PATH.read_text(encoding="utf-8")
        cfg = llm_client.load_config("script_writer")

        prompt = script_writer.build_script_prompt(story, framework, body.idea_prompt, prompt_template)
        text, model_used = script_writer.generate_script(prompt, cfg)

        script_writer.init_db(conn)
        duration_target = float(framework.get("duration_sec") or 0.0)
        script_id = script_writer.save_script(
            conn, body.story_node_id, body.framework_id, body.idea_prompt,
            text, model_used, duration_target,
        )
        created_row = conn.execute(
            "SELECT created_at FROM reel_scripts WHERE id = ?",
            (script_id,),
        ).fetchone()
        return {
            "script_id": script_id,
            "generated_text": text,
            "story_node_id": body.story_node_id,
            "framework_id": body.framework_id,
            "model_used": model_used,
            "created_at": created_row["created_at"] if created_row else None,
        }
    finally:
        conn.close()


@router.get("/scripts")
def list_scripts():
    conn = _db()
    try:
        rows = conn.execute(
            "SELECT id, story_node_id, framework_id, model_used, created_at "
            "FROM reel_scripts ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]
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
