import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
from .models import RecommendationRequest, GenerateRequest, ContentDraft
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
    story_node_id: Optional[str] = None
    framework_id: str
    idea_prompt: Optional[str] = None
    provider: str = "ollama"
    model: str = "gemma3:latest"


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
    req = GenerateRequest(
        story_node_id=body.story_node_id,
        framework_id=body.framework_id,
        idea_prompt=body.idea_prompt,
        provider=body.provider,
        model=body.model,
    )
    with get_connection() as conn:
        try:
            result = service.generate_draft(conn, req)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc))
    return asdict(result)


@router.post("/generate/stream")
async def generate_draft_stream(body: GenerateRequestBody):
    from openrouter.router import stream as llm_stream

    req = GenerateRequest(
        story_node_id=body.story_node_id,
        framework_id=body.framework_id,
        idea_prompt=body.idea_prompt,
        provider=body.provider,
        model=body.model,
    )
    with get_connection() as conn:
        try:
            prompt, framework_id, story_node_id_saved = service.prepare_prompt(conn, req)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    messages = [{"role": "user", "content": prompt}]
    override = None
    if body.provider == "openrouter" and body.model:
        override = body.model
    elif body.provider == "ollama":
        override = f"ollama:{body.model}"

    async def event_generator():
        try:
            async for chunk in llm_stream("generate_linkedin_post", messages, max_tokens=1024, override_model=override):
                if chunk["type"] == "done":
                    conn2 = get_connection()
                    try:
                        draft = ContentDraft(
                            story_node_id=story_node_id_saved,
                            framework_id=framework_id,
                            idea_prompt=body.idea_prompt,
                            generated_text=chunk["content"],
                            model_used=chunk["model"],
                        )
                        draft_id = repository.save_draft(conn2, draft)
                        try:
                            conn2.execute(
                                "UPDATE content_drafts SET cost_usd = ? WHERE id = ?",
                                (chunk.get("cost_usd", 0.0), draft_id),
                            )
                            conn2.commit()
                        except Exception:
                            pass
                        chunk["draft_id"] = draft_id
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
            "asana_task_gid, posted_at "
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
