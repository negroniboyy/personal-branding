# Personal Brand Monorepo — 2026-05-02

**Stack:** Python 3.12 · uv · notion-client==2.2.1 · SQLite · FastAPI · React+Vite · Whisper · PySceneDetect · ffprobe · Ollama gemma-32k · **v1.5**

## Status
v1.4 reels pipeline + v1.5 centralized logger. `shared/logger.py` at repo root wired into narrative_warehouse, instagram_frameworks, linkedin_frameworks. 7-day auto-purge. Logs land in `personal_brand/logs/`.

## File Map
| File | Role |
|------|------|
| `NOTION DIARY FETCHER/api/main.py` | FastAPI app — mounts narrative_router + content_writer_router |
| `NOTION DIARY FETCHER/config.toml` | All deps config; `[logger]` section added |
| `shared/shared/logger.py` | Centralized logger factory — `get_logger(subsystem)` |
| `shared/pyproject.toml` | Local uv package; installed into NOTION DIARY FETCHER venv |
| `content_writer/api_routes.py` | /content-writer router (frameworks, recommendations, generate, drafts) |
| `frameworks/instagram_frameworks/extract_reel.py` | Reel .mp4 → reel_frameworks table |
| `frameworks/instagram_frameworks/script_writer.py` | story_nodes × reel_frameworks → reel_scripts table |
| `frameworks/instagram_frameworks/llm_client.py` | Ollama client; reads config.toml; logger wired |
| `frameworks/linkedin_frameworks/extract_linkedin.py` | LinkedIn .txt → frameworks table |
| `narrative_warehouse/stage1_extractor.py` | Diary pages → story_nodes; logger wired |
| `narrative_warehouse/stage2_synthesizer.py` | story_nodes → weekly_index + threads; logger wired |
| `frontend/src/components/ContentWriter.jsx` | Story+framework picker, generate, drafts panel |

## Run Commands
```bash
# Backend
cd "NOTION DIARY FETCHER" && uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
# Frontend
cd frontend && npm run dev   # http://localhost:5173
# Sync diary
cd "NOTION DIARY FETCHER" && uv run sync
# Extract reel framework (run from NOTION DIARY FETCHER/)
uv run python ../frameworks/instagram_frameworks/extract_reel.py --file ../frameworks/instagram_frameworks/references/<file>.mp4
# Generate reel script
uv run python ../frameworks/instagram_frameworks/script_writer.py [--idea TEXT] [--story-id ID] [--framework-id ID] [--dry-run]
# After adding new deps to shared/
cd "NOTION DIARY FETCHER" && uv sync
```

## Edit Here When...
| Change | File |
|--------|------|
| Logger level or retention | `NOTION DIARY FETCHER/config.toml` `[logger]` |
| Logger factory logic | `shared/shared/logger.py` |
| Add logging to a new subsystem | `from shared.logger import get_logger` at module top; add name to CLAUDE.md §7 |
| Reel extraction prompt / pacing | `frameworks/instagram_frameworks/prompts/extract_reel.txt` |
| Reel script format / scene template | `frameworks/instagram_frameworks/prompts/script_writer.txt` |
| Notion API auth or pagination | `NOTION DIARY FETCHER/src/notion_fetcher/client.py` |
| SQLite schema or upsert | `NOTION DIARY FETCHER/src/notion_fetcher/database.py` |
| Frontend UI changes | `frontend/src/components/ContentWriter.jsx` |

## Active Context
- **Done:** v1.5 logger shipped — `shared/shared/logger.py`, `uv sync` installs it, wired into narrative_warehouse (stage1, stage2, api_routes, llm_client) + instagram_frameworks (extract_reel, script_writer, llm_client) + linkedin_frameworks (extract_linkedin, llm_client); CLAUDE.md §7 added; logs/ at repo root; 7-day purge verified
- **Next:** populate more reel references in `frameworks/instagram_frameworks/references/`; first real `script_writer.py` end-to-end run; manual `visual_notes` UPDATE per reel
- **Notes:** `shared` is a uv editable dep — run `uv sync` from `NOTION DIARY FETCHER/` after any `shared/pyproject.toml` changes; reel CLIs must run from `NOTION DIARY FETCHER/` for venv resolution; `NOTION DIARY FETCHER/ui/` is stale (superseded by `frontend/`) — safe to delete
