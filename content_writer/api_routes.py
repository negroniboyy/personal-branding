from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

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
