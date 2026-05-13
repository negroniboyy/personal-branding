# Personal Brand Monorepo — 2026-05-13

**Stack:** Python 3.12 · uv · FastAPI · SQLite · React 18 · Vite · Tailwind v3.4 · framer-motion v11 · **Run:** `./start.sh` (3 Terminal tabs) · **v1.7**

## Status
5-tab React frontend (Diary / Narrative / Writer / Reels / Ideas) wired to two FastAPI services on :8000 and :8001. v1.7 adds Ideas: capture spontaneous insights, generate LinkedIn drafts or Reel scripts inline without requiring a story node.

## File Map
| File | Role |
|------|------|
| `NOTION DIARY FETCHER/api/main.py` | FastAPI :8000 — mounts narrative, content_writer, reel, sync routers |
| `NOTION DIARY FETCHER/api/reel_routes.py` | /reels router (generate, scan, open-folder) |
| `NOTION DIARY FETCHER/config.toml` | All config: `ollama_model`, `[logger]`, `[script_writer]` |
| `Ideas Draft/main.py` | FastAPI :8001 — 6 /ideas endpoints + startup DB migration |
| `Ideas Draft/repository.py` | DB queries: ideas table, idea_id FK linkage to drafts/scripts |
| `content_writer/service.py` | LinkedIn draft generation; uses `ollama_model` from config |
| `content_writer/repository.py` | story_nodes / frameworks / drafts queries |
| `frameworks/instagram_frameworks/script_writer.py` | story_nodes × reel_frameworks → reel_scripts |
| `shared/shared/logger.py` | `get_logger(subsystem)` — logs to `personal_brand/logs/` |
| `frontend/src/App.jsx` | Tab router — 5 tabs including Ideas |
| `frontend/src/components/layout/Sidebar.jsx` | 5-item nav; "New Idea" fires `create-idea` CustomEvent |
| `frontend/src/components/IdeasTab.jsx` | Master-detail ideas list |
| `frontend/src/components/IdeaDetail.jsx` | Editable title/body, inline generate, child drafts list |
| `frontend/src/ideasApi.js` | Fetch wrappers for :8001 |
| `frontend/tailwind.config.js` | StudioBrand design tokens |

## Edit Here When...
| Change | File |
|--------|------|
| Add/rename sidebar tabs | `Sidebar.jsx` + `App.jsx` |
| Ideas API endpoints | `Ideas Draft/main.py` |
| Ideas DB schema | `Ideas Draft/repository.py` → `run_migration()` |
| LinkedIn generation model | `NOTION DIARY FETCHER/config.toml` → `[content_writer] ollama_model` |
| Reel generation model | `NOTION DIARY FETCHER/config.toml` → `[script_writer] ollama_model` |
| Notion sync / diary fetch | `NOTION DIARY FETCHER/src/notion_fetcher/sync.py` |
| Design tokens / glass styles | `frontend/tailwind.config.js` + `frontend/src/index.css` |
| Reel extraction prompt | `frameworks/instagram_frameworks/prompts/extract_reel.txt` |

## Active Context
- **Done:** v1.7 Ideas feature — `Ideas Draft/` FastAPI service, master-detail IdeasTab, inline LinkedIn + Reel generation, `idea_id` FK on drafts/scripts, `start.sh` launches all 3 services, `ollama_model` fixed to `gemma4:e2b`.
- **Next:** Delete 2 blank test ideas (`idea_e867ca43`, `idea_538f4d2b`); add delete-idea endpoint if needed.
- **Notes:** `Ideas Draft/` directory has a space — uvicorn must run from inside it. Story node IDs are TEXT (`sn_xxx`). Shared DB: `NOTION DIARY FETCHER/data/notion_diary.db`. Tailwind v3 only.
