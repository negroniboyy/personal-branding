import sqlite3
import sys
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
from .prompt_builder import build_freeform_prompt

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "openrouter"))


def get_recommendations(
    conn: sqlite3.Connection,
    req: RecommendationRequest,
) -> RecommendationResult:
    frameworks = repository.get_frameworks(conn)
    scored_frameworks = recommender.score_frameworks(frameworks, req.idea_prompt)

    return RecommendationResult(
        stories=[],
        frameworks=scored_frameworks[: req.top_n],
    )


def prepare_prompt(
    conn: sqlite3.Connection,
    req: GenerateRequest,
) -> tuple[str, int, Optional[int]]:
    """Build and return (prompt, framework_id, story_node_id_saved) without calling LLM."""
    run_migration(conn)

    frameworks = repository.get_frameworks(conn)
    framework = next((f for f in frameworks if f.id == req.framework_id), None)
    if not framework:
        raise ValueError(f"framework_id {req.framework_id} not found")

    if not req.idea_prompt:
        raise ValueError("idea_prompt is required")
    prompt = build_freeform_prompt(req.idea_prompt, framework)
    story_node_id_saved = None

    from shared.lifecycle import get_feedback_block
    prompt += get_feedback_block(conn, "content_drafts")

    return prompt, req.framework_id, story_node_id_saved


def generate_draft(
    conn: sqlite3.Connection,
    req: GenerateRequest,
    framework_pick_reason: Optional[str] = None,
) -> GenerateResult:
    from openrouter.router import chat as llm_chat

    prompt, framework_id, story_node_id_saved = prepare_prompt(conn, req)
    messages = [{"role": "user", "content": prompt}]

    override = req.model or None
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
        framework_pick_reason=framework_pick_reason,
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
        framework_pick_reason=framework_pick_reason,
    )
