import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

from jobs import queue as jobs_queue

from . import repository
from .models import (
    GenerateDraftRequest,
    Idea,
    IdeaWithDrafts,
    PatchIdeaRequest,
    PatchIdeaTierRequest,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

router = APIRouter(tags=["ideas"])


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/ideas", response_model=list[Idea])
def list_ideas():
    conn = _db()
    try:
        return repository.list_ideas(conn)
    finally:
        conn.close()


@router.post("/ideas", response_model=Idea, status_code=201)
def create_idea():
    idea_id = "idea_" + uuid.uuid4().hex[:8]
    conn = _db()
    try:
        return repository.create_idea(conn, idea_id, _now())
    finally:
        conn.close()


@router.get("/ideas/{idea_id}", response_model=IdeaWithDrafts)
def get_idea(idea_id: str):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")
        drafts = repository.get_idea_drafts(conn, idea_id)
        return IdeaWithDrafts(idea=idea, drafts=drafts)
    finally:
        conn.close()


@router.delete("/ideas/{idea_id}")
def delete_idea(idea_id: str):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")
        return repository.delete_idea_cascade(conn, idea_id)
    finally:
        conn.close()


@router.delete("/ideas/{idea_id}/drafts/{draft_id}")
def delete_idea_draft(idea_id: str, draft_id: int, channel: Literal["linkedin", "reel"] = "linkedin"):
    conn = _db()
    try:
        if channel == "linkedin":
            deleted = repository.delete_linkedin_draft(conn, idea_id, draft_id)
        else:
            deleted = repository.delete_reel_script(conn, idea_id, draft_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"draft {draft_id} not found for idea {idea_id!r}")
        return {"deleted": True}
    finally:
        conn.close()


@router.patch("/ideas/{idea_id}", response_model=Idea)
def patch_idea(idea_id: str, body: PatchIdeaRequest):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")
        repository.patch_idea(conn, idea_id, body.title, body.body, _now())
        return repository.get_idea(conn, idea_id)
    finally:
        conn.close()


@router.post("/ideas/{idea_id}/drafts/linkedin")
def generate_linkedin(idea_id: str, body: GenerateDraftRequest):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")

        idea_prompt = body.idea_prompt or idea.body or idea.title or None
        if not idea_prompt:
            raise HTTPException(status_code=422, detail="Idea has no text — add a title or body before generating")
    finally:
        conn.close()

    job_id = jobs_queue.enqueue("generate_linkedin_draft", {
        "idea_id": idea_id,
        "idea_prompt": idea_prompt,
        "framework_id": body.framework_id,
    })
    return {"job_id": job_id}


@router.post("/ideas/{idea_id}/drafts/reel")
def generate_reel(idea_id: str, body: GenerateDraftRequest):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")

        idea_prompt = body.idea_prompt or idea.body or idea.title or None
        if not idea_prompt:
            raise HTTPException(status_code=422, detail="Idea has no text — add a title or body before generating")
    finally:
        conn.close()

    job_id = jobs_queue.enqueue("generate_reel_script", {
        "idea_id": idea_id,
        "idea_prompt": idea_prompt,
        "framework_id": body.framework_id,
        "tier": idea.tier or "scripted-headshot",
    })
    return {"job_id": job_id}


@router.patch("/ideas/{idea_id}/tier", response_model=Idea)
def patch_idea_tier(idea_id: str, body: PatchIdeaTierRequest):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")
        repository.set_idea_tier(conn, idea_id, body.tier, _now())
        return repository.get_idea(conn, idea_id)
    finally:
        conn.close()
