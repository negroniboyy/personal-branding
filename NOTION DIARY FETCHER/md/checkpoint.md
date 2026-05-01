# Notion Diary Fetcher — 2026-04-25

**Stack:** Python 3.12 · uv · notion-client==2.2.1 · sqlite3 · FastAPI · React+Vite · **Run:** `uv run sync` · **v1.2**

## Status
CLI syncs Notion diary DB → SQLite (pages/blocks/chunks). 83 pages synced. FastAPI backend working with CORS. React UI implemented and verified.

## File Map
| File | Role |
|------|------|
| `main.py` | CLI entrypoint — loads .env + config.toml, calls run_sync |
| `src/notion_fetcher/client.py` | Notion API wrapper — pagination, rate limit, recursive blocks |
| `src/notion_fetcher/database.py` | SQLite schema + upsert — pages, blocks, chunks tables |
| `src/notion_fetcher/sync.py` | Orchestration — fetch → upsert → prune stale pages |
| `src/notion_fetcher/chunker.py` | Text chunker — 500-token chunks prefixed with [title] |
| `config.toml` | DB path, rate limit delay, chunk size, page size |
| `api/main.py` | FastAPI backend — GET /pages, GET /pages/{id}, CORS enabled |
| `api/requirements.txt` | fastapi + uvicorn deps for API server |
| `data/notion_diary.db` | SQLite output — gitignored, created at runtime |
| `ui/` | React + Vite frontend (port 5173) |
| `ui/src/App.jsx` | Root component — selectedPageId state |
| `ui/src/api.js` | fetchPages(), fetchPage() to localhost:8000 |
| `ui/src/components/PageList.jsx` | Page list with clickable titles+dates |
| `ui/src/components/PageDetail.jsx` | Page detail with blocks + back button |
| `handoff/` | Blueprints for local LLM handoff (Gemma4/Qwen) |

## Run Commands
```bash
# API backend
cd /Users/maxkiyuna/Documents/personal_brand/NOTION\ DIARY\ FETCHER
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000

# UI frontend (separate terminal)
cd /Users/maxkiyuna/Documents/personal_brand/NOTION\ DIARY\ FETCHER/ui
npm run dev
```

## Edit Here When...
| Change | File |
|--------|------|
| Notion API auth or pagination | `src/notion_fetcher/client.py` |
| SQLite schema or upsert logic | `src/notion_fetcher/database.py` |
| Chunk size or title prefix format | `src/notion_fetcher/chunker.py` |
| DB path or rate limit config | `config.toml` |
| Add API endpoint | `api/main.py` |
| Add React UI component | `ui/src/components/` |

## Active Context
- **Done:** Notion→SQLite sync (83 pages, 2023 blocks, 119 chunks); FastAPI + CORS; React UI verified working
- **Fix:** api/main.py sys.path — `parent.parent.parent` to reach personal_brand/ for narrative_warehouse import
- **Next:** ???
- **Notes:** notion-client must stay pinned to ==2.2.1 (v3.0.0 broke databases.query)


|------ Using the Frameworks with Diary ------|
The framework files in frameworks/linkedin_frameworks/frameworks are structural templates: hook type, tone, paragraph style, CTA, and an ordered argument pattern. The database in notion_diary.db gives the raw material. story_nodes is the best source for post-level narrative because it already contains:

user_state = emotional/context setup
conflict_node = tension/problem
desired_outcome = transformation target
the_bridge = core insight
thematic_tags = topic matching
worth_score = prioritization

weekly_index is better for editorial planning than for a single post body. It tells you what themes repeated in a week and which tensions are worth packaging next.

A practical mapping looks like this:

Framework hook = derived from conflict_node + the_bridge
Body tension = user_state + source chunks
Promise/outcome = desired_outcome
Topic fit = thematic_tags
Priority = worth_score
Publishing angle for the week = weekly_index.thread_summary_json