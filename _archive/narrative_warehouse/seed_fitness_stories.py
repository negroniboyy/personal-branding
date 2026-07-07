"""
One-shot seeder: inserts 5 hand-authored fitness story_nodes.
Idempotent — uses INSERT OR IGNORE on the synthetic page_id.

Run from repo root:
    cd "NOTION DIARY FETCHER" && uv run python -m narrative_warehouse.seed_fitness_stories
"""

import json
from datetime import datetime, timezone

from shared.logger import get_logger
from .db import get_db

logger = get_logger("narrative_warehouse")

_NOW = datetime.now(timezone.utc).isoformat()
_MODEL = "manual:seed-fitness-v1"

_STORIES = [
    {
        "id": "seed-fitness-001",
        "page_id": "seed-fitness-001",
        "created_time": _NOW,
        "user_state": "Dealing with a knee and pelvis injury that forced me to stop heavy powerlifting",
        "conflict_node": "Physical limit colliding with ambition — injury forced a complete training reset",
        "desired_outcome": "Rebuild strength through mobility and plyometrics without ego or shortcuts",
        "the_bridge": "Runner friends introduced inner-muscle drills and resistance work; legs got stronger, not weaker",
        "thematic_tags": json.dumps(["fitness", "building", "philosophy", "injury", "reset", "mobility"]),
        "worth_score": 0.92,
        "narrative_flag": "High Narrative Potential",
        "llm_model_used": _MODEL,
        "processed_at": _NOW,
    },
    {
        "id": "seed-fitness-002",
        "page_id": "seed-fitness-002",
        "created_time": _NOW,
        "user_state": "Frustrated that no fitness app tracked exactly what I needed; limited coding skills",
        "conflict_node": "The gap between what I needed and what existing apps offered — so I built my own",
        "desired_outcome": "A self-hosted fitness tracker (Turbo Baba) running on GCP that works for me",
        "the_bridge": "Vibe-coded it with limited knowledge, learned as I built, shipped something that looks and works like a real app",
        "thematic_tags": json.dumps(["fitness", "building", "ai", "turbo-baba", "vibe-coding", "gcp", "solo-builder"]),
        "worth_score": 0.90,
        "narrative_flag": "High Narrative Potential",
        "llm_model_used": _MODEL,
        "processed_at": _NOW,
    },
    {
        "id": "seed-fitness-003",
        "page_id": "seed-fitness-003",
        "created_time": _NOW,
        "user_state": "Afraid of long distances — had never run 15km before and dreaded the attempt",
        "conflict_node": "Fear of long runs as a psychological barrier, not just a physical one",
        "desired_outcome": "Overcome the fear and make 15km+ feel normal, including trail running",
        "the_bridge": "Gradually increased load over the past month, ran 15km twice, trail runs on the side",
        "thematic_tags": json.dumps(["fitness", "running", "philosophy", "fear", "long-distance", "trail"]),
        "worth_score": 0.88,
        "narrative_flag": "High Narrative Potential",
        "llm_model_used": _MODEL,
        "processed_at": _NOW,
    },
    {
        "id": "seed-fitness-004",
        "page_id": "seed-fitness-004",
        "created_time": _NOW,
        "user_state": "Running speed has dropped significantly since ramping up mileage and bulking",
        "conflict_node": "Speed loss feels like regression but it is actually a necessary phase",
        "desired_outcome": "Accept slower pace now to build a stronger base — trust the process",
        "the_bridge": "Reframing: speed is not the metric right now; consistency and base-building are. It is just a matter of time.",
        "thematic_tags": json.dumps(["fitness", "running", "philosophy", "anti-performance", "patience", "non-performative"]),
        "worth_score": 0.95,
        "narrative_flag": "High Narrative Potential",
        "llm_model_used": _MODEL,
        "processed_at": _NOW,
    },
    {
        "id": "seed-fitness-005",
        "page_id": "seed-fitness-005",
        "created_time": _NOW,
        "user_state": "Calisthenics skills — especially muscle-ups — completely gone after a long hiatus",
        "conflict_node": "Skill regression after deprioritising calisthenics; muscle-ups no longer there",
        "desired_outcome": "Honest return to basics without ego; rebuild foundation before attempting skills again",
        "the_bridge": "Accepted the regression as data, not failure. Going back to beginner progressions intentionally.",
        "thematic_tags": json.dumps(["fitness", "calisthenics", "philosophy", "regression", "honest-builder", "back-to-basics"]),
        "worth_score": 0.87,
        "narrative_flag": "High Narrative Potential",
        "llm_model_used": _MODEL,
        "processed_at": _NOW,
    },
]


def seed() -> int:
    conn = get_db(ro=False)
    inserted = 0
    try:
        for s in _STORIES:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO story_nodes
                (id, page_id, created_time, user_state, conflict_node, desired_outcome,
                 the_bridge, thematic_tags, worth_score, narrative_flag, llm_model_used, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["id"], s["page_id"], s["created_time"],
                    s["user_state"], s["conflict_node"], s["desired_outcome"],
                    s["the_bridge"], s["thematic_tags"], s["worth_score"],
                    s["narrative_flag"], s["llm_model_used"], s["processed_at"],
                ),
            )
            inserted += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return inserted


if __name__ == "__main__":
    n = seed()
    print(f"Seeded {n} fitness story_nodes." if n else "Seeded 0 fitness story_nodes (already present).")
    logger.info("seed_fitness_stories: inserted %d rows", n)
