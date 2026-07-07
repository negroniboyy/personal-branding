import argparse
import json
import uuid
from datetime import datetime, timezone, timedelta

from shared.logger import get_logger
from .db import get_db, run_migrations
from .normalizer import normalize_conflict_node, display_name_from_conflict_node

logger = get_logger("narrative_warehouse")


def get_week_bounds(week_start: str | None = None) -> tuple[str, str]:
    if week_start:
        start = datetime.fromisoformat(week_start)
    else:
        today = datetime.now(timezone.utc)
        start = today - timedelta(days=today.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6)
    return start.date().isoformat(), end.date().isoformat()


def compute_sentiment_delta(nodes: list) -> float:
    if len(nodes) < 2:
        return 0.0
    sorted_nodes = sorted(nodes, key=lambda n: n["created_time"])
    mid = len(sorted_nodes) // 2
    early = sorted_nodes[:mid] if mid > 0 else sorted_nodes
    late = sorted_nodes[mid:] if mid > 0 else sorted_nodes
    early_avg = sum(n["worth_score"] for n in early) / len(early)
    late_avg = sum(n["worth_score"] for n in late) / len(late)
    return round(late_avg - early_avg, 4)


def classify_thread_status(occurrence_count: int, sentiment_delta: float) -> str:
    if occurrence_count == 1:
        return "Emerging"
    if sentiment_delta >= 0.15:
        return "Closing"
    return "Open"


def run_synthesis(week_start: str | None = None) -> dict:
    run_migrations()

    ws, we = get_week_bounds(week_start)

    conn = get_db(ro=False)

    cursor = conn.execute(
        """
        SELECT id, conflict_node, created_time, worth_score
        FROM story_nodes
        WHERE date(created_time) >= date(?) AND date(created_time) <= date(?)
        ORDER BY created_time
        """,
        (ws, we),
    )
    nodes = cursor.fetchall()

    if not nodes:
        return {
            "status": "success",
            "week_index_id": f"weekly_{ws}",
            "total_entries": 0,
            "thread_count": 0,
            "open_loops": 0,
            "closed_loops": 0,
            "sentiment_delta": 0.0,
            "message": "No story nodes found for this week",
        }

    grouped: dict[str, list] = {}
    for node in nodes:
        norm = normalize_conflict_node(node["conflict_node"])
        grouped.setdefault(norm, []).append(dict(node))

    thread_summaries = []
    open_loops = 0
    closed_loops = 0

    for norm_conflict, group in grouped.items():
        first_seen = min(n["created_time"] for n in group)
        last_seen = max(n["created_time"] for n in group)
        avg_score = sum(n["worth_score"] for n in group) / len(group)
        sentiment_delta = compute_sentiment_delta(group)
        status = classify_thread_status(len(group), sentiment_delta)

        existing = conn.execute(
            "SELECT id, occurrence_count FROM threads WHERE conflict_node = ?", (norm_conflict,)
        ).fetchone()

        now_iso = datetime.now(timezone.utc).isoformat()

        if existing:
            thread_id = existing["id"]
            new_count = existing["occurrence_count"] + len(group)
            cursor.execute(
                """
                UPDATE threads
                SET last_seen = ?, occurrence_count = ?, current_status = ?,
                    closed_week_start = CASE WHEN ? = 'Closed' THEN ? ELSE closed_week_start END
                WHERE id = ?
                """,
                (last_seen, new_count, status, status, ws, thread_id),
            )
        else:
            thread_id = f"thread_{uuid.uuid4().hex[:12]}"
            display = display_name_from_conflict_node(norm_conflict)
            cursor.execute(
                """
                INSERT INTO threads
                (id, conflict_node, display_name, first_seen, last_seen,
                 occurrence_count, current_status, closed_week_start)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (thread_id, norm_conflict, display, first_seen, last_seen, len(group), status, ws if status == "Closed" else None),
            )

        if status in ("Open", "Closing", "Emerging"):
            open_loops += 1
        elif status == "Closed":
            closed_loops += 1

        thread_summaries.append({
            "conflict_node": norm_conflict,
            "display_name": display_name_from_conflict_node(norm_conflict),
            "occurrence_count": len(group),
            "avg_worth_score": round(avg_score, 3),
            "sentiment_delta": sentiment_delta,
            "current_status": status,
        })

    total_entries = len(nodes)
    thread_count = len(grouped)
    overall_sentiment_delta = compute_sentiment_delta(nodes)

    weekly_id = f"weekly_{ws}"
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT INTO weekly_index
        (id, week_start, week_end, total_entries, thread_count, open_loops,
         closed_loops, sentiment_delta, thread_summary_json, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            week_end = excluded.week_end,
            total_entries = excluded.total_entries,
            thread_count = excluded.thread_count,
            open_loops = excluded.open_loops,
            closed_loops = excluded.closed_loops,
            sentiment_delta = excluded.sentiment_delta,
            thread_summary_json = excluded.thread_summary_json,
            generated_at = excluded.generated_at
        """,
        (
            weekly_id, ws, we, total_entries, thread_count, open_loops,
            closed_loops, overall_sentiment_delta, json.dumps(thread_summaries), now_iso,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "week_index_id": weekly_id,
        "total_entries": total_entries,
        "thread_count": thread_count,
        "open_loops": open_loops,
        "closed_loops": closed_loops,
        "sentiment_delta": overall_sentiment_delta,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 2: Synthesize weekly threads from recent story nodes")
    parser.add_argument("--week-start", help="ISO date (YYYY-MM-DD) of the Monday to synthesize")
    args = parser.parse_args()

    result = run_synthesis(args.week_start)
    logger.info("synthesis complete: %s", json.dumps(result))
    print(json.dumps(result, indent=2))