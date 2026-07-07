"""HTTP API for Instagram Reels: script generation + manual MP4 ingest."""

import sqlite3
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
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
import script_writer
from shared.lifecycle import (
    CAPTION_PROMPT,
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

router = APIRouter(prefix="/reels", tags=["reels"])


class RecommendationRequestBody(BaseModel):
    idea_prompt: Optional[str] = None
    top_n: int = 20
    domain: Optional[str] = None


class GenerateRequestBody(BaseModel):
    framework_id: Optional[str] = None
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
    conn = _db()
    try:
        all_fw = script_writer.load_reel_frameworks(conn)
        scored = script_writer.score_frameworks({}, all_fw, body.idea_prompt)
        frameworks = scored[:body.top_n]
        return {"frameworks": frameworks}
    finally:
        conn.close()


@router.post("/generate")
def generate(body: GenerateRequestBody):
    if not body.idea_prompt:
        raise HTTPException(status_code=422, detail="idea_prompt is required")

    from jobs import queue as jobs_queue
    job_id = jobs_queue.enqueue("generate_reel_script", {
        "idea_id": None,
        "idea_prompt": body.idea_prompt,
        "framework_id": body.framework_id,
        "model": body.model,
    })
    return {"job_id": job_id}


@router.get("/scripts")
def list_scripts(status: Optional[str] = None, limit: int = 100):
    """Returns one card per idea (the LIVE version — highest version among
    non-killed rows, falling back to the highest version if all are killed)
    plus every one-off script (idea_id IS NULL, always its own family of one)."""
    conn = _db()
    try:
        rows = conn.execute(
            "SELECT id, story_node_id, framework_id, model_used, created_at, "
            "generated_text, status, verdict, verdict_note, caption, cta, "
            "asana_task_gid, posted_at, framework_pick_reason, idea_id, tier, version "
            "FROM reel_scripts ORDER BY created_at DESC"
        ).fetchall()

        by_idea: dict[str, list[dict]] = {}
        one_offs: list[dict] = []
        for r in rows:
            d = dict(r)
            if d["idea_id"]:
                by_idea.setdefault(d["idea_id"], []).append(d)
            else:
                one_offs.append(d)

        live = []
        for idea_rows in by_idea.values():
            non_killed = [r for r in idea_rows if (r["status"] or "queued") != "killed"]
            pool = non_killed or idea_rows
            live.append(max(pool, key=lambda r: r["version"] or 1))

        result = live + one_offs
        if status:
            result = [r for r in result if (r["status"] or "queued") == status]
        result.sort(key=lambda r: r["created_at"] or "", reverse=True)
        return result[:limit]
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
        if updated.get("idea_id"):
            from jobs import queue as jobs_queue
            jobs_queue.enqueue("push_notion_status", {"idea_id": updated["idea_id"]})
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


@router.get("/scripts/{script_id}/versions")
def get_script_versions(script_id: int):
    """All rows sharing this script's idea_id (its version family), newest first.
    One-off scripts (no idea_id) are always a family of one."""
    conn = _db()
    try:
        row = conn.execute("SELECT idea_id FROM reel_scripts WHERE id = ?", (script_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"reel_script {script_id} not found")
        idea_id = row["idea_id"]
        if idea_id:
            rows = conn.execute(
                "SELECT id, version, status, created_at, model_used, generated_text, tier "
                "FROM reel_scripts WHERE idea_id = ? ORDER BY version DESC",
                (idea_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, version, status, created_at, model_used, generated_text, tier "
                "FROM reel_scripts WHERE id = ? ORDER BY version DESC",
                (script_id,),
            ).fetchall()
        return [dict(r) for r in rows]
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
    """Enqueue one background job per .mp4 in the references folder, plus one per
    .mp4 in references/beat_edit/ (music-driven, minimal/no-VO reels — extracted via
    a vision pass instead of Whisper transcript). The jobs worker runs them one at a
    time (same serialization the old lock gave us), so this returns immediately —
    poll each job_id via GET /jobs/{id}."""
    from jobs import queue as jobs_queue
    from extract_reel import BEAT_EDIT_REFERENCES_DIR

    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    BEAT_EDIT_REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in REFERENCES_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".mp4")
    beat_edit_files = sorted(p for p in BEAT_EDIT_REFERENCES_DIR.iterdir() if p.suffix.lower() == ".mp4")

    jobs = [
        {"file": f.name, "job_id": jobs_queue.enqueue("scan_reference_file", {"file_path": str(f)})}
        for f in files
    ] + [
        {"file": f"beat_edit/{f.name}", "job_id": jobs_queue.enqueue("scan_beat_edit_reference_file", {"file_path": str(f)})}
        for f in beat_edit_files
    ]
    return {"queued": len(jobs), "jobs": jobs, "references_dir": str(REFERENCES_DIR)}
