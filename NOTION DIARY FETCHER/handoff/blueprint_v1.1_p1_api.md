# Blueprint v1.1 — Part 1/2: FastAPI Backend
# Notion Diary UI — Backend API

**Feed order:** p1 (this) → p2 (React UI)
**Execution target:** Qwen via Continue

---

## STATE

Existing files (do not touch):
```
src/notion_fetcher/        # Python sync package
data/notion_diary.db       # SQLite database
pyproject.toml
```

New files to create:
```
api/main.py                # FastAPI app
api/requirements.txt       # fastapi, uvicorn only
```

---

## SPECS

- Python 3.12
- FastAPI + uvicorn (standalone, NOT part of uv project)
- sqlite3 stdlib — read-only access to ../data/notion_diary.db
- CORS enabled for localhost:5173 (Vite dev server)
- No auth — local dev only

---

## ENDPOINTS

### GET /pages
Returns list of all pages, ordered by created_time DESC.

Response shape:
```json
[
  {
    "id": "string",
    "title": "string",
    "created_time": "string",
    "last_edited_time": "string",
    "url": "string"
  }
]
```

SQL: `SELECT id, title, created_time, last_edited_time, url FROM pages ORDER BY created_time DESC`

---

### GET /pages/{page_id}
Returns a single page with all its blocks in order.

Response shape:
```json
{
  "id": "string",
  "title": "string",
  "created_time": "string",
  "url": "string",
  "blocks": [
    {
      "block_type": "string",
      "plain_text": "string | null",
      "position": 0
    }
  ]
}
```

SQL:
```sql
SELECT id, title, created_time, url FROM pages WHERE id = ?
SELECT block_type, plain_text, position FROM blocks
  WHERE page_id = ? ORDER BY position
```

Return 404 if page not found.

---

## MODULE SIGNATURES

```
api/main.py

  app = FastAPI()
  DB_PATH = Path(__file__).parent.parent / "data" / "notion_diary.db"

  def get_db() -> sqlite3.Connection
    # opens read-only connection, sets row_factory = sqlite3.Row

  GET /pages -> list[PageSummary]
  GET /pages/{page_id} -> PageDetail | 404
  GET /health -> {"status": "ok"}
```

---

## RUN COMMAND

```bash
cd api
pip install fastapi uvicorn
uvicorn main:app --reload --port 8000
```

---

## DONE FOR PART 1

After API is working (`curl http://localhost:8000/pages` returns JSON), feed Part 2.
