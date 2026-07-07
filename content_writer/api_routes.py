import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from shared.lifecycle import (
    CAPTION_PROMPT,
    parse_package_output,
    save_package,
    update_meta,
)
from shared.md_mirror import delete_draft_md, write_draft_md
from .db import get_connection, run_migration
from .models import RecommendationRequest
from . import service, repository

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

router = APIRouter(prefix="/content-writer", tags=["content-writer"])


# --- Request/Response schemas (Pydantic) ---

class RecommendationRequestBody(BaseModel):
    idea_prompt: Optional[str] = None
    top_n: int = 20
    domain: Optional[str] = None


class GenerateRequestBody(BaseModel):
    framework_id: Optional[str] = None
    idea_prompt: Optional[str] = None
    provider: str = "openrouter"
    model: Optional[str] = None  # None -> use config/openrouter_models.yaml cascade


class PatchDraftBody(BaseModel):
    generated_text: str


class MetaBody(BaseModel):
    status: Optional[str] = None
    verdict: Optional[int] = None
    verdict_note: Optional[str] = None
    asana_task_gid: Optional[str] = None


class PackageBody(BaseModel):
    model: Optional[str] = None


# One-time schema upgrade so /meta and /package work before any generation runs.
try:
    with get_connection() as _conn:
        run_migration(_conn)
except Exception:
    pass


# --- Routes ---

@router.get("/frameworks")
def list_frameworks():
    with get_connection() as conn:
        from .repository import get_frameworks
        frameworks = get_frameworks(conn)
    return [asdict(f) for f in frameworks]


@router.post("/recommendations")
def get_recommendations(body: RecommendationRequestBody):
    req = RecommendationRequest(idea_prompt=body.idea_prompt, top_n=body.top_n, domain=body.domain)
    with get_connection() as conn:
        result = service.get_recommendations(conn, req)
    return {
        "stories": [asdict(s) for s in result.stories],
        "frameworks": [asdict(f) for f in result.frameworks],
    }


@router.post("/generate")
def generate_draft(body: GenerateRequestBody):
    if not body.idea_prompt:
        raise HTTPException(status_code=422, detail="idea_prompt is required")

    from jobs import queue as jobs_queue
    job_id = jobs_queue.enqueue("generate_linkedin_draft", {
        "idea_id": None,
        "idea_prompt": body.idea_prompt,
        "framework_id": body.framework_id,
        "model": body.model,
    })
    return {"job_id": job_id}


@router.get("/drafts")
def list_drafts(status: Optional[str] = None, limit: int = 100):
    with get_connection() as conn:
        where, params = "", []
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(limit)
        rows = conn.execute(
            "SELECT id, story_node_id, framework_id, idea_prompt, generated_text, "
            "model_used, created_at, status, verdict, verdict_note, caption, cta, "
            "asana_task_gid, posted_at, framework_pick_reason "
            f"FROM content_drafts {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


@router.patch("/drafts/{draft_id}/meta")
def patch_draft_meta(draft_id: int, body: MetaBody):
    with get_connection() as conn:
        try:
            updated = update_meta(conn, "content_drafts", draft_id, body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found")
    if updated.get("idea_id"):
        from jobs import queue as jobs_queue
        jobs_queue.enqueue("push_notion_status", {"idea_id": updated["idea_id"]})
    return updated


@router.post("/drafts/{draft_id}/package")
def package_draft(draft_id: int, body: PackageBody):
    """Generate caption + CTA for a REVIEWED draft. Rejected while still queued."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Draft not found")
        if (row["status"] or "queued") in ("queued", "killed"):
            raise HTTPException(
                status_code=409,
                detail="draft must be approved (reviewed) before packaging caption/CTA",
            )
        from openrouter.router import chat as llm_chat
        result = llm_chat(
            "generate_linkedin_post",
            [{"role": "user", "content": CAPTION_PROMPT.format(content=row["generated_text"])}],
            max_tokens=512,
            override_model=body.model or None,
        )
        caption, cta = parse_package_output(result["content"])
        save_package(conn, "content_drafts", draft_id, caption, cta)
    return {"draft_id": draft_id, "caption": caption, "cta": cta, "model_used": result["model"]}


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: int):
    with get_connection() as conn:
        from .repository import get_draft as _get
        draft = _get(conn, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return asdict(draft)


@router.patch("/drafts/{draft_id}")
def patch_draft(draft_id: int, body: PatchDraftBody):
    with get_connection() as conn:
        from .repository import update_draft
        draft = update_draft(conn, draft_id, body.generated_text)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    row = asdict(draft)
    try:
        write_draft_md(row)
    except Exception as e:
        from shared.logger import get_logger
        get_logger("md_mirror").warning("write_draft_md failed on patch id=%s: %s", draft_id, e)
    return row


@router.delete("/drafts/{draft_id}")
def delete_draft_route(draft_id: int):
    with get_connection() as conn:
        from .repository import delete_draft
        deleted = delete_draft(conn, draft_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
    try:
        delete_draft_md(draft_id)
    except Exception as e:
        from shared.logger import get_logger
        get_logger("md_mirror").warning("delete_draft_md failed for id=%s: %s", draft_id, e)
    return {"ok": True}


@router.post("/open-folder")
def open_drafts_folder():
    from shared.md_mirror import _load_dirs
    _, drafts_dir = _load_dirs()
    drafts_dir.mkdir(parents=True, exist_ok=True)
    plat = sys.platform
    if plat == "darwin":
        subprocess.Popen(["open", str(drafts_dir)])
    elif plat.startswith("linux"):
        subprocess.Popen(["xdg-open", str(drafts_dir)])
    else:
        raise HTTPException(status_code=501, detail=f"open-folder not supported on {plat}")
    return {"opened": True, "path": str(drafts_dir)}
