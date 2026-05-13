import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Repo root on sys.path so content_writer + reel modules are importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_INSTAGRAM_FW_DIR = _REPO_ROOT / "frameworks" / "instagram_frameworks"
_SHARED_DIR = _REPO_ROOT / "shared"
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_INSTAGRAM_FW_DIR))
sys.path.insert(0, str(_SHARED_DIR))

from content_writer.db import get_connection as _cw_conn, run_migration as _cw_migration
from content_writer.service import generate_draft as _cw_generate, get_recommendations as _cw_recs
from content_writer.models import GenerateRequest, RecommendationRequest
import script_writer
import llm_client

import repository
from models import (
    GenerateDraftRequest,
    Idea,
    IdeaWithDrafts,
    PatchIdeaRequest,
)

DB_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"
SCRIPT_PROMPT_PATH = script_writer.PROMPT_PATH

app = FastAPI(title="Ideas Draft", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.on_event("startup")
def startup():
    conn = _db()
    try:
        _cw_migration(conn)      # ensures content_drafts exists
        repository.run_migration(conn)  # creates ideas + adds idea_id columns
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Ideas CRUD
# ---------------------------------------------------------------------------

@app.get("/ideas", response_model=list[Idea])
def list_ideas():
    conn = _db()
    try:
        return repository.list_ideas(conn)
    finally:
        conn.close()


@app.post("/ideas", response_model=Idea, status_code=201)
def create_idea():
    idea_id = "idea_" + uuid.uuid4().hex[:8]
    conn = _db()
    try:
        return repository.create_idea(conn, idea_id, _now())
    finally:
        conn.close()


@app.get("/ideas/{idea_id}", response_model=IdeaWithDrafts)
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


@app.patch("/ideas/{idea_id}", response_model=Idea)
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


# ---------------------------------------------------------------------------
# Generation endpoints
# ---------------------------------------------------------------------------

@app.post("/ideas/{idea_id}/drafts/linkedin")
def generate_linkedin(idea_id: str, body: GenerateDraftRequest):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")

        idea_prompt = body.idea_prompt or idea.body or idea.title or None
        story_node_id = body.story_node_id
        framework_id = body.framework_id

        # Auto-pick story/framework if not provided
        if not story_node_id or not framework_id:
            rec_req = RecommendationRequest(idea_prompt=idea_prompt, top_n=1)
            recs = _cw_recs(conn, rec_req)
            if not story_node_id and recs.stories:
                story_node_id = recs.stories[0].id
            if not framework_id and recs.frameworks:
                framework_id = recs.frameworks[0].id

        if not story_node_id or not framework_id:
            raise HTTPException(status_code=422, detail="No stories or frameworks available")

        gen_req = GenerateRequest(
            story_node_id=story_node_id,
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
            "story_node_id": str(result.story_node_id),
            "model_used": result.model_used,
        }
    finally:
        conn.close()


@app.post("/ideas/{idea_id}/drafts/reel")
def generate_reel(idea_id: str, body: GenerateDraftRequest):
    conn = _db()
    try:
        idea = repository.get_idea(conn, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"idea {idea_id!r} not found")

        idea_prompt = body.idea_prompt or idea.body or idea.title or None
        story_node_id = body.story_node_id
        framework_id = body.framework_id

        # Auto-pick story if not provided
        if not story_node_id:
            stories = script_writer.load_story_nodes(conn, limit=1)
            if stories:
                story_node_id = stories[0]["id"]

        if not story_node_id:
            raise HTTPException(status_code=422, detail="No story nodes available")

        # Auto-pick reel framework if not provided
        all_fw = script_writer.load_reel_frameworks(conn)
        if not framework_id and all_fw:
            if idea_prompt:
                story_row = conn.execute(
                    "SELECT * FROM story_nodes WHERE id = ?", (story_node_id,)
                ).fetchone()
                if story_row:
                    scored = script_writer.score_frameworks(dict(story_row), all_fw, idea_prompt)
                    framework_id = scored[0]["id"] if scored else all_fw[0]["id"]
                else:
                    framework_id = all_fw[0]["id"]
            else:
                framework_id = all_fw[0]["id"]

        if not framework_id:
            raise HTTPException(status_code=422, detail="No reel frameworks available")

        fw_row = conn.execute("SELECT * FROM reel_frameworks WHERE id = ?", (framework_id,)).fetchone()
        if not fw_row:
            raise HTTPException(status_code=404, detail=f"reel_framework {framework_id!r} not found")

        story_row = conn.execute("SELECT * FROM story_nodes WHERE id = ?", (story_node_id,)).fetchone()
        if not story_row:
            raise HTTPException(status_code=404, detail=f"story_node {story_node_id!r} not found")

        prompt_template = SCRIPT_PROMPT_PATH.read_text(encoding="utf-8")
        cfg = llm_client.load_config("script_writer")
        prompt = script_writer.build_script_prompt(dict(story_row), dict(fw_row), idea_prompt, prompt_template)
        text, model_used = script_writer.generate_script(prompt, cfg)

        script_writer.init_db(conn)
        duration_target = float(fw_row["duration_sec"] or 0.0)
        script_id = script_writer.save_script(
            conn, story_node_id, framework_id, idea_prompt, text, model_used, duration_target,
        )
        repository.link_reel(conn, script_id, idea_id)

        return {
            "id": script_id,
            "channel": "reel",
            "generated_text": text,
            "framework_id": framework_id,
            "story_node_id": story_node_id,
            "model_used": model_used,
        }
    finally:
        conn.close()
