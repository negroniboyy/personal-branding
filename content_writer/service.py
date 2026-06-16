import sqlite3
import sys
import tomllib
from pathlib import Path
from typing import Optional

from shared.md_mirror import write_draft_md

from . import recommender, repository
from .db import get_connection, run_migration
from .models import (
    ContentDraft,
    GenerateRequest,
    GenerateResult,
    RecommendationRequest,
    RecommendationResult,
)
from .prompt_builder import build_freeform_prompt, build_prompt

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "NOTION DIARY FETCHER" / "config.toml"
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "openrouter"))


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
    min_worth = cfg.get("min_worth_score", 0.0)
    nodes = repository.get_story_nodes(conn, limit=limit, min_worth_score=min_worth, domain=req.domain)
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


def prepare_prompt(
    conn: sqlite3.Connection,
    req: GenerateRequest,
) -> tuple[str, int, Optional[int]]:
    """Build and return (prompt, framework_id, story_node_id_saved) without calling LLM."""
    cfg = _load_config()
    run_migration(conn)

    frameworks = repository.get_frameworks(conn)
    framework = next((f for f in frameworks if f.id == req.framework_id), None)
    if not framework:
        raise ValueError(f"framework_id {req.framework_id} not found")

    if req.story_node_id is None:
        if not req.idea_prompt:
            raise ValueError("idea_prompt is required when story_node_id is None")
        prompt = build_freeform_prompt(req.idea_prompt, framework)
        story_node_id_saved = None
    else:
        nodes = repository.get_story_nodes(conn, limit=200)
        story = next((n for n in nodes if n.id == req.story_node_id), None)
        if not story:
            raise ValueError(f"story_node_id {req.story_node_id} not found")
        chunks = repository.get_chunks_for_story(conn, req.story_node_id)
        max_chars = cfg.get("max_source_chars", 12_000)
        prompt = build_prompt(story, framework, chunks, req.idea_prompt, max_chars)
        story_node_id_saved = req.story_node_id

    from shared.lifecycle import get_feedback_block
    prompt += get_feedback_block(conn, "content_drafts")

    return prompt, req.framework_id, story_node_id_saved


def generate_draft(
    conn: sqlite3.Connection,
    req: GenerateRequest,
) -> GenerateResult:
    from openrouter.router import chat as llm_chat

    prompt, framework_id, story_node_id_saved = prepare_prompt(conn, req)
    messages = [{"role": "user", "content": prompt}]

    # Determine override model: if provider is openrouter pass the model; ollama goes to tier-3
    override = None
    if req.provider == "openrouter" and req.model:
        override = req.model
    elif req.provider == "ollama":
        cfg = _load_config()
        ollama_model = req.model if req.model != "gemma3:latest" else cfg.get("ollama_model", req.model)
        override = f"ollama:{ollama_model}"

    # Original Ollama call (now tier-3 fallback via router):
    # text = llm_client.generate(prompt, provider=req.provider, model=model, ollama_host=ollama_host)
    result = llm_chat("generate_linkedin_post", messages, max_tokens=1024, override_model=override)
    text = result["content"]
    model_used = result["model"]
    cost_usd = result.get("cost_usd", 0.0)

    draft = ContentDraft(
        story_node_id=story_node_id_saved,
        framework_id=framework_id,
        idea_prompt=req.idea_prompt,
        generated_text=text,
        model_used=model_used,
    )
    draft_id = repository.save_draft(conn, draft)
    created_row = conn.execute(
        "SELECT created_at FROM content_drafts WHERE id = ?", (draft_id,)
    ).fetchone()
    try:
        conn.execute(
            "UPDATE content_drafts SET cost_usd = ? WHERE id = ?",
            (cost_usd, draft_id),
        )
        conn.commit()
    except Exception:
        pass
    try:
        write_draft_md({
            "id": draft_id,
            "story_node_id": draft.story_node_id,
            "framework_id": draft.framework_id,
            "model_used": model_used,
            "created_at": created_row["created_at"] if created_row else None,
            "generated_text": text,
        })
    except Exception as e:
        from shared.logger import get_logger as _get_logger
        _get_logger("md_mirror").warning("write_draft_md failed for id=%s: %s", draft_id, e)

    return GenerateResult(
        draft_id=draft_id,
        generated_text=text,
        story_node_id=story_node_id_saved,
        framework_id=framework_id,
        model_used=model_used,
    )
