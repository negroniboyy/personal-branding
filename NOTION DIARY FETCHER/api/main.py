from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys
import sqlite3

# Narrative Warehouse API routes
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from narrative_warehouse.api_routes import router as narrative_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(narrative_router)

from content_writer.api_routes import router as content_writer_router
app.include_router(content_writer_router)

from api.reel_routes import router as reel_router
app.include_router(reel_router)

DB_PATH = Path(__file__).parent.parent / "data" / "notion_diary.db"


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
    """Health check endpoint."""
    return {"status": "ok"}


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