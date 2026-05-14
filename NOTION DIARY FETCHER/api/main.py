from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timezone
import sys
import os
import threading
import tomllib
import sqlite3

from dotenv import load_dotenv

# Narrative Warehouse API routes
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from narrative_warehouse.api_routes import router as narrative_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(narrative_router)

from content_writer.api_routes import router as content_writer_router
app.include_router(content_writer_router)

from api.reel_routes import router as reel_router
app.include_router(reel_router)

from ideas.routes import router as ideas_router
app.include_router(ideas_router)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "frameworks"))
from api_routes import router as frameworks_router
app.include_router(frameworks_router)

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
_ENV_PATH = Path(__file__).parent.parent / ".env"
_CONFIG_PATH = Path(__file__).parent.parent / "config.toml"

_sync_state: dict = {"status": "idle", "started_at": None, "finished_at": None, "error": None, "added": None}
_sync_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_sync_job():
    global _sync_state
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        load_dotenv(_ENV_PATH)
        token = os.environ.get("NOTION_TOKEN")
        database_id = os.environ.get("NOTION_DATABASE_ID")
        if not token or not database_id:
            raise ValueError("NOTION_TOKEN and NOTION_DATABASE_ID must be set in .env")

        with open(_CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)

        conn = sqlite3.connect(str(DB_PATH))
        pre_count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        conn.close()

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from notion_fetcher.sync import run_sync
        run_sync(token=token, database_id=database_id, config=config)

        conn = sqlite3.connect(str(DB_PATH))
        post_count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        conn.close()

        _sync_state.update(status="ok", finished_at=_now_iso(), error=None, added=post_count - pre_count)
    except Exception as exc:
        _sync_state.update(status="error", finished_at=_now_iso(), error=str(exc), added=None)
    finally:
        _sync_lock.release()


def get_db() -> sqlite3.Connection:
    """Open read-only connection to SQLite database."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


class PageSummary(BaseModel):
    id: str
    title: str
    created_time: str
    last_edited_time: str
    url: str


class Block(BaseModel):
    block_type: str
    plain_text: str | None
    position: int


class PageDetail(BaseModel):
    id: str
    title: str
    created_time: str
    url: str
    blocks: list[Block]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    if _sync_state["status"] == "running":
        raise HTTPException(status_code=409, detail="sync already running")
    _sync_state.update(status="running", started_at=_now_iso(), finished_at=None, error=None, added=None)
    background_tasks.add_task(_run_sync_job)
    return {"status": "running", "started_at": _sync_state["started_at"]}


@app.get("/sync/status")
def sync_status():
    return dict(_sync_state)


@app.get("/pages")
def get_pages() -> list[PageSummary]:
    """Returns list of all pages, ordered by created_time DESC."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, title, created_time, last_edited_time, url FROM pages ORDER BY created_time DESC"
        )
        rows = cursor.fetchall()
        return [
            PageSummary(
                id=row["id"],
                title=row["title"],
                created_time=row["created_time"],
                last_edited_time=row["last_edited_time"],
                url=row["url"],
            )
            for row in rows
        ]
    finally:
        conn.close()


@app.get("/pages/{page_id}")
def get_page(page_id: str) -> PageDetail:
    """Returns a single page with all its blocks in order."""
    conn = get_db()
    try:
        cursor = conn.execute("SELECT id, title, created_time, url FROM pages WHERE id = ?", (page_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Page not found")

        cursor = conn.execute(
            "SELECT block_type, plain_text, position FROM blocks WHERE page_id = ? ORDER BY position",
            (page_id,)
        )
        rows = cursor.fetchall()

        blocks = [
            Block(
                block_type=row["block_type"],
                plain_text=row["plain_text"],
                position=row["position"],
            )
            for row in rows
        ]

        return PageDetail(
            id=row["id"],
            title=row["title"],
            created_time=row["created_time"],
            url=row["url"],
            blocks=blocks,
        )
    finally:
        conn.close()