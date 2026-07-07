from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from content_writer.api_routes import router as content_writer_router
app.include_router(content_writer_router)

from api.reel_routes import router as reel_router
app.include_router(reel_router)

from ideas.routes import router as ideas_router
app.include_router(ideas_router)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "frameworks"))
from api_routes import router as frameworks_router
app.include_router(frameworks_router)

from jobs.routes import router as jobs_router
app.include_router(jobs_router)

from notion_ideas.routes import router as notion_ideas_router
app.include_router(notion_ideas_router)


@app.get("/openrouter/models")
def list_openrouter_models():
    import yaml
    config_path = Path(__file__).parent.parent.parent / "config" / "openrouter_models.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return {
        task: {
            "chain": [m for m in (v.get("primary"), v.get("secondary")) if m] + v.get("options", []),
            "default": v["primary"],
        }
        for task, v in config["tasks"].items()
    }

DB_PATH = Path(__file__).parent.parent / "data" / "notion_diary.db"


@app.on_event("startup")
def _run_migrations() -> None:
    from content_writer.db import run_migration as _cw_migration
    from content_writer.repository import get_drafts
    from ideas import repository as _ideas_repo
    from shared.md_mirror import backfill_drafts, backfill_scripts
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "frameworks" / "instagram_frameworks"))
    import script_writer as _sw
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.row_factory = sqlite3.Row
        _cw_migration(conn)
        _sw.init_db(conn)
        _ideas_repo.run_migration(conn)

        # Backfill MD mirrors for any existing rows that lack files
        script_rows = conn.execute(
            "SELECT id, story_node_id, framework_id, model_used, created_at, generated_text "
            "FROM reel_scripts"
        ).fetchall()
        backfill_scripts([dict(r) for r in script_rows])

        drafts = get_drafts(conn, limit=10000)
        from dataclasses import asdict
        backfill_drafts([asdict(d) for d in drafts])
    finally:
        conn.close()

    from jobs import queue as jobs_queue
    jobs_queue.run_migration()
    recovered = jobs_queue.recover_stale_jobs()
    if recovered:
        import logging
        logging.getLogger("jobs").warning("marked %d stale 'running' job(s) as failed on startup", recovered)
    jobs_queue.start_worker()


@app.get("/health")
def health():
    return {"status": "ok"}