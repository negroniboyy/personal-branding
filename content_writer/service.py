import sqlite3
import tomllib
from pathlib import Path
from typing import Optional

from . import llm_client, recommender, repository
from .db import get_connection, run_migration
from .models import (
    ContentDraft,
    GenerateRequest,
    GenerateResult,
    RecommendationRequest,
    RecommendationResult,
)
from .prompt_builder import build_prompt

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "NOTION DIARY FETCHER" / "config.toml"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "rb") as f:
            return tomllib.load(f).get("content_writer", {})
    except FileNotFoundError:
        return {}


def get_recommendations(
    conn: sqlite3.Connection,
    req: RecommendationRequest,
) -> RecommendationResult:
    cfg = _load_config()
    limit = cfg.get("default_story_limit", 20)
    nodes = repository.get_story_nodes(conn, limit=limit)
    frameworks = repository.get_frameworks(conn)
    weekly = repository.get_latest_weekly_index(conn)

    scored_stories = recommender.score_stories(nodes, weekly, req.idea_prompt)
    top_story = scored_stories[0] if scored_stories else None
    scored_frameworks = (
        recommender.score_frameworks(frameworks, top_story, req.idea_prompt)
        if top_story
        else frameworks
    )

    return RecommendationResult(
        stories=scored_stories[: req.top_n],
        frameworks=scored_frameworks[: req.top_n],
    )


def generate_draft(
    conn: sqlite3.Connection,
    req: GenerateRequest,
) -> GenerateResult:
    cfg = _load_config()
    run_migration(conn)

    nodes = repository.get_story_nodes(conn, limit=200)
    story = next((n for n in nodes if n.id == req.story_node_id), None)
    if not story:
        raise ValueError(f"story_node_id {req.story_node_id} not found")

    frameworks = repository.get_frameworks(conn)
    framework = next((f for f in frameworks if f.id == req.framework_id), None)
    if not framework:
        raise ValueError(f"framework_id {req.framework_id} not found")

    chunks = repository.get_chunks_for_story(conn, req.story_node_id)
    max_chars = cfg.get("max_source_chars", 12_000)
    prompt = build_prompt(story, framework, chunks, req.idea_prompt, max_chars)

    ollama_host = cfg.get("ollama_host", "http://localhost:11434")
    text = llm_client.generate(
        prompt,
        provider=req.provider,
        model=req.model,
        ollama_host=ollama_host,
    )

    draft = ContentDraft(
        story_node_id=req.story_node_id,
        framework_id=req.framework_id,
        idea_prompt=req.idea_prompt,
        generated_text=text,
        model_used=f"{req.provider}/{req.model}",
    )
    draft_id = repository.save_draft(conn, draft)

    return GenerateResult(
        draft_id=draft_id,
        generated_text=text,
        story_node_id=req.story_node_id,
        framework_id=req.framework_id,
        model_used=draft.model_used,
    )
