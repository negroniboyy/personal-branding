import subprocess
import sys
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from shared.md_mirror import delete_draft_md, write_draft_md
from .db import get_connection
from .models import RecommendationRequest, GenerateRequest
from . import service

router = APIRouter(prefix="/content-writer", tags=["content-writer"])


# --- Request/Response schemas (Pydantic) ---

class RecommendationRequestBody(BaseModel):
    idea_prompt: Optional[str] = None
    top_n: int = 5


class GenerateRequestBody(BaseModel):
    story_node_id: int
    framework_id: int
    idea_prompt: Optional[str] = None
    provider: str = "ollama"
    model: str = "gemma3:latest"


class PatchDraftBody(BaseModel):
    generated_text: str


# --- Routes ---

@router.get("/frameworks")
def list_frameworks():
    with get_connection() as conn:
        from .repository import get_frameworks
        frameworks = get_frameworks(conn)
    return [asdict(f) for f in frameworks]


@router.post("/recommendations")
def get_recommendations(body: RecommendationRequestBody):
    req = RecommendationRequest(idea_prompt=body.idea_prompt, top_n=body.top_n)
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


@router.get("/drafts")
def list_drafts():
    with get_connection() as conn:
        from .repository import get_drafts
        drafts = get_drafts(conn)
    return [asdict(d) for d in drafts]


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
