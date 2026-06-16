import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INSTAGRAM_FW_DIR = _REPO_ROOT / "frameworks" / "instagram_frameworks"
if str(_INSTAGRAM_FW_DIR) not in sys.path:
    sys.path.insert(0, str(_INSTAGRAM_FW_DIR))

from content_writer.service import generate_draft as _cw_generate, get_recommendations as _cw_recs
from content_writer.models import GenerateRequest, RecommendationRequest
import script_writer
import llm_client

from . import repository
from .models import (
    GenerateDraftRequest,
    Idea,
    IdeaWithDrafts,
    PatchIdeaRequest,
)

DB_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"
SCRIPT_PROMPT_PATH = script_writer.PROMPT_PATH

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

        framework_id = body.framework_id
        if not framework_id:
            recs = _cw_recs(conn, RecommendationRequest(idea_prompt=idea_prompt, top_n=1))
            if not recs.frameworks:
                raise HTTPException(status_code=422, detail="No LinkedIn frameworks available")
            framework_id = recs.frameworks[0].id

        gen_req = GenerateRequest(
            story_node_id=None,
            framework_id=framework_id,
            idea_prompt=idea_prompt,
        )
        result = _cw_generate(conn, gen_req)
        repository.link_draft(conn, result.draft_id, idea_id)

        return {
            "id": result.draft_id,
            "channel": "linkedin",
            "generated_text": result.generated_text,
            "framework_id": str(result.framework_id),
            "story_node_id": None,
            "model_used": result.model_used,
        }
    finally:
        conn.close()


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

        framework_id = body.framework_id
        all_fw = script_writer.load_reel_frameworks(conn)
        if not all_fw:
            raise HTTPException(status_code=422, detail="No reel frameworks available")

        if not framework_id:
            scored = script_writer.score_frameworks({}, all_fw, idea_prompt)
            framework_id = scored[0]["id"] if scored else all_fw[0]["id"]

        fw_row = conn.execute("SELECT * FROM reel_frameworks WHERE id = ?", (framework_id,)).fetchone()
        if not fw_row:
            raise HTTPException(status_code=404, detail=f"reel_framework {framework_id!r} not found")

        prompt = script_writer.build_freeform_script_prompt(idea_prompt, dict(fw_row))
        cfg = llm_client.load_config("script_writer")
        text, model_used = script_writer.generate_script(prompt, cfg)

        script_writer.init_db(conn)
        duration_target = float(fw_row["duration_sec"] or 0.0)
        script_id = script_writer.save_script(
            conn, None, framework_id, idea_prompt, text, model_used, duration_target,
        )
        repository.link_reel(conn, script_id, idea_id)

        return {
            "id": script_id,
            "channel": "reel",
            "generated_text": text,
            "framework_id": framework_id,
            "story_node_id": None,
            "model_used": model_used,
        }
    finally:
        conn.close()
