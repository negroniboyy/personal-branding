import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .stage1_extractor import run_extraction
from .stage2_synthesizer import run_synthesis
from .db import get_db

router = APIRouter(prefix="/narrative", tags=["narrative"])


class ExtractRequest(BaseModel):
    provider: str | None = None
    model: str | None = None


class SynthesizeRequest(BaseModel):
    week_start: str | None = None


class UpdateStoryNodeRequest(BaseModel):
    user_state: str | None = None
    conflict_node: str | None = None
    desired_outcome: str | None = None
    the_bridge: str | None = None
    thematic_tags: list[str] | None = None
    worth_score: float | None = None
    narrative_flag: str | None = None


@router.post("/extract")
def extract(req: ExtractRequest = None) -> dict[str, Any]:
    provider = req.provider if req else None
    model = req.model if req else None
    result = run_extraction(provider=provider, model=model)
    if result.get("errors") and result["pages_processed"] == 0:
        raise HTTPException(status_code=500, detail=result["errors"])
    return result


@router.post("/synthesize")
def synthesize(req: SynthesizeRequest = None) -> dict[str, Any]:
    week_start = req.week_start if req else None
    result = run_synthesis(week_start=week_start)
    return result


@router.get("/story-nodes")
def list_story_nodes(
    since: str | None = None,
    until: str | None = None,
    min_score: float | None = None,
    narrative_flag: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    conn = get_db(ro=True)
    try:
        conditions = []
        params = []

        if since:
            conditions.append("date(created_time) >= date(?)")
            params.append(since)
        if until:
            conditions.append("date(created_time) <= date(?)")
            params.append(until)
        if min_score is not None:
            conditions.append("worth_score >= ?")
            params.append(min_score)
        if narrative_flag:
            conditions.append("narrative_flag = ?")
            params.append(narrative_flag)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM story_nodes WHERE {where_clause}",
            params,
        ).fetchone()
        total = count_row["cnt"]

        rows = conn.execute(
            f"""
            SELECT id, page_id, created_time, user_state, conflict_node,
                   desired_outcome, the_bridge, thematic_tags, worth_score,
                   narrative_flag, llm_model_used, processed_at
            FROM story_nodes
            WHERE {where_clause}
            ORDER BY created_time DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

        items = []
        for row in rows:
            items.append({
                "id": row["id"],
                "page_id": row["page_id"],
                "created_time": row["created_time"],
                "user_state": row["user_state"],
                "conflict_node": row["conflict_node"],
                "desired_outcome": row["desired_outcome"],
                "the_bridge": row["the_bridge"],
                "thematic_tags": row["thematic_tags"],
                "worth_score": row["worth_score"],
                "narrative_flag": row["narrative_flag"],
                "llm_model_used": row["llm_model_used"],
                "processed_at": row["processed_at"],
            })

        return {"items": items, "total": total, "limit": limit, "offset": offset}
    finally:
        conn.close()


@router.put("/story-nodes/{node_id}")
def update_story_node(node_id: str, req: UpdateStoryNodeRequest) -> dict[str, Any]:
    conn = get_db(ro=False)
    try:
        existing = conn.execute(
            "SELECT id FROM story_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Story node not found")

        fields = []
        values = []
        if req.user_state is not None:
            fields.append("user_state = ?"); values.append(req.user_state)
        if req.conflict_node is not None:
            fields.append("conflict_node = ?"); values.append(req.conflict_node)
        if req.desired_outcome is not None:
            fields.append("desired_outcome = ?"); values.append(req.desired_outcome)
        if req.the_bridge is not None:
            fields.append("the_bridge = ?"); values.append(req.the_bridge)
        if req.thematic_tags is not None:
            import json
            fields.append("thematic_tags = ?"); values.append(json.dumps(req.thematic_tags))
        if req.worth_score is not None:
            fields.append("worth_score = ?"); values.append(req.worth_score)
        if req.narrative_flag is not None:
            fields.append("narrative_flag = ?"); values.append(req.narrative_flag)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(node_id)
        conn.execute(f"UPDATE story_nodes SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()

        row = conn.execute(
            """SELECT id, page_id, created_time, user_state, conflict_node,
                      desired_outcome, the_bridge, thematic_tags, worth_score,
                      narrative_flag, llm_model_used, processed_at
               FROM story_nodes WHERE id = ?""",
            (node_id,),
        ).fetchone()

        return {
            "id": row["id"],
            "page_id": row["page_id"],
            "created_time": row["created_time"],
            "user_state": row["user_state"],
            "conflict_node": row["conflict_node"],
            "desired_outcome": row["desired_outcome"],
            "the_bridge": row["the_bridge"],
            "thematic_tags": row["thematic_tags"],
            "worth_score": row["worth_score"],
            "narrative_flag": row["narrative_flag"],
            "llm_model_used": row["llm_model_used"],
            "processed_at": row["processed_at"],
        }
    finally:
        conn.close()


@router.get("/weekly-index")
def list_weekly_index(limit: int = Query(default=10, le=50)) -> dict[str, Any]:
    conn = get_db(ro=True)
    try:
        rows = conn.execute(
            """
            SELECT id, week_start, week_end, total_entries, thread_count,
                   open_loops, closed_loops, sentiment_delta, thread_summary_json, generated_at
            FROM weekly_index
            ORDER BY week_start DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return {
            "items": [
                {
                    "id": row["id"],
                    "week_start": row["week_start"],
                    "week_end": row["week_end"],
                    "total_entries": row["total_entries"],
                    "thread_count": row["thread_count"],
                    "open_loops": row["open_loops"],
                    "closed_loops": row["closed_loops"],
                    "sentiment_delta": row["sentiment_delta"],
                    "thread_summary_json": row["thread_summary_json"],
                    "generated_at": row["generated_at"],
                }
                for row in rows
            ]
        }
    finally:
        conn.close()


@router.get("/threads")
def list_threads(
    status: str | None = None,
    limit: int = Query(default=20, le=100),
) -> dict[str, Any]:
    conn = get_db(ro=True)
    try:
        if status:
            rows = conn.execute(
                """
                SELECT id, conflict_node, display_name, first_seen, last_seen,
                       occurrence_count, current_status, closed_week_start
                FROM threads
                WHERE current_status = ?
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, conflict_node, display_name, first_seen, last_seen,
                       occurrence_count, current_status, closed_week_start
                FROM threads
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return {
            "items": [
                {
                    "id": row["id"],
                    "conflict_node": row["conflict_node"],
                    "display_name": row["display_name"],
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"],
                    "occurrence_count": row["occurrence_count"],
                    "current_status": row["current_status"],
                    "closed_week_start": row["closed_week_start"],
                }
                for row in rows
            ]
        }
    finally:
        conn.close()