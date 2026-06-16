# Personal Brand System

_Last updated: 2026-05-27_

## What it is
A content creation pipeline that turns Max's Notion diary into LinkedIn + Instagram posts.

## Pipeline
```
Notion Diary → Stage1 Extractor (Claude Sonnet) → story_nodes (SQLite)
→ Content Writer UI → LinkedIn / Instagram drafts → MD mirror (scripts/ + drafts/)
```

## Current Status (from checkpoint 2026-05-15)
- **v2.0 shipped:** domain-chip filter (5 domains), worth_score ≥ 0.70 floor, top_n raised to 20, 5 fitness story_nodes seeded
- **95 total stories, 83 pass the floor, 10 fitness-tagged**
- **82 diary pages unprocessed** (`processed_status=0`) — Stage1 extractor ready but deferred

## Domains
`Building` · `Career` · `AI` · `Fitness` · `Philosophy`

## Active Asana Tasks
- Make a cron for framework extraction and the diary fetcher
- Create a general post manager tab (new frontend tab — manage LinkedIn + Instagram content schedule)
- Test script for new LinkedIn references

## Next Steps (from checkpoint)
1. Restart `./start.sh` → verify chips render + fitness filter
2. Ship 5 posts from existing story_nodes
3. Re-plan Phase 1 — mine 82 unprocessed diary pages with Stage1 extractor

## Key Files
| File | Role |
|------|------|
| `NOTION DIARY FETCHER/api/main.py` | FastAPI :8000 |
| `NOTION DIARY FETCHER/config.toml` | All config (worth_score floor, ollama model, logger) |
| `content_writer/repository.py` | `get_story_nodes()` — domain + worth_score filter |
| `narrative_warehouse/` | Story storage subsystem |
| `frameworks/instagram_frameworks/` | Instagram script generation |
| `frameworks/linkedin_frameworks/` | LinkedIn post generation |
| `frontend/src/lib/domains.js` | Single source of truth for domain vocabulary |
| `shared/shared/logger.py` | Shared logger — `get_logger("subsystem_name")` |

## Run
```bash
./start.sh   # opens 2 terminal tabs: FastAPI :8000 + Vite frontend
```
