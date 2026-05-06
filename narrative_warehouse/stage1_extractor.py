import argparse
import json
import time
import uuid
from datetime import datetime, timezone

from shared.logger import get_logger
from .config import NarrativeWarehouseConfig, get_llm_provider_override, get_llm_model_override
from .db import get_db, run_migrations
from .llm_client import make_llm_client

logger = get_logger("narrative_warehouse")


def build_diary_text(conn, page_id: str) -> str:
    cursor = conn.execute(
        "SELECT plain_text FROM blocks WHERE page_id = ? AND plain_text IS NOT NULL ORDER BY position",
        (page_id,),
    )
    rows = cursor.fetchall()
    return "\n".join(row["plain_text"] for row in rows)


def run_extraction(provider: str | None = None, model: str | None = None) -> dict:
    run_migrations()

    effective_provider = provider or get_llm_provider_override() or NarrativeWarehouseConfig.llm_provider
    effective_model = model or get_llm_model_override() or NarrativeWarehouseConfig.llm_model

    llm = make_llm_client(effective_provider, effective_model)

    conn = get_db(ro=False)
    cursor = conn.execute(
        "SELECT id, title, created_time FROM pages WHERE processed_status = 0 ORDER BY created_time DESC"
    )
    pages = cursor.fetchall()

    errors = []
    nodes_created = 0
    low_potential_count = 0
    start = time.time()

    for page_row in pages:
        page_id = page_row["id"]
        diary_text = build_diary_text(conn, page_id)

        if not diary_text.strip():
            conn.execute("UPDATE pages SET processed_status = 1 WHERE id = ?", (page_id,))
            conn.commit()
            continue

        try:
            result = llm.extract_story_variables(diary_text)
            now_iso = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO story_nodes
                (id, page_id, created_time, user_state, conflict_node, desired_outcome,
                 the_bridge, thematic_tags, worth_score, narrative_flag, llm_model_used, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"sn_{uuid.uuid4().hex[:12]}",
                    page_id,
                    page_row["created_time"],
                    result.user_state,
                    result.conflict_node,
                    result.desired_outcome,
                    result.the_bridge,
                    json.dumps(result.thematic_tags),
                    result.worth_score,
                    result.narrative_flag,
                    f"{effective_provider}:{effective_model}",
                    now_iso,
                ),
            )
            conn.execute("UPDATE pages SET processed_status = 1 WHERE id = ?", (page_id,))
            conn.commit()
            nodes_created += 1
            if result.narrative_flag == "Low Narrative Potential":
                low_potential_count += 1

        except Exception as e:
            logger.error("Page %s extraction failed: %s", page_id, e)
            errors.append(f"Page {page_id}: {str(e)}")

    conn.close()
    duration = time.time() - start

    return {
        "status": "success",
        "pages_processed": len(pages),
        "story_nodes_created": nodes_created,
        "low_potential_count": low_potential_count,
        "errors": errors,
        "model_used": f"{effective_provider}:{effective_model}",
        "duration_seconds": round(duration, 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 1: Extract story nodes from unprocessed diary pages")
    parser.add_argument("--provider", choices=["ollama", "minimax"], help="Override LLM provider")
    parser.add_argument("--model", help="Override LLM model")
    args = parser.parse_args()

    result = run_extraction(args.provider, args.model)
    logger.info("extraction complete: %s", json.dumps(result))
    print(json.dumps(result, indent=2))