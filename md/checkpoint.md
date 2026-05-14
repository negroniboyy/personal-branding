# Personal Brand Monorepo — 2026-05-14

**Stack:** Python 3.12 · uv · FastAPI · SQLite · React 18 · Vite · Tailwind v3.4 · framer-motion v11 · **Run:** `./start.sh` (2 Terminal tabs) · **v1.9**

## Status
6-tab React frontend (Diary / Narrative / Writer / Reels / Ideas / Frameworks) wired to a single FastAPI on :8000. v1.9 adds disk MD mirror for scripts/drafts (DB primary), inline edit/delete/open-folder on Reels + Content Writer, full Frameworks CRUD tab, and intelligent framework titles synced across dropdowns.

## File Map
| File | Role |
|------|------|
| `NOTION DIARY FETCHER/api/main.py` | FastAPI :8000 — mounts narrative, content_writer, reel, ideas, frameworks routers; startup runs migrations + MD backfill |
| `NOTION DIARY FETCHER/api/reel_routes.py` | /reels router — generate, scan, open-scripts-folder, PATCH/DELETE script + MD mirror |
| `NOTION DIARY FETCHER/config.toml` | All config: `ollama_model`, `[logger]`, `[script_writer]`, `[md_mirror] scripts_dir / drafts_dir` |
| `shared/shared/md_mirror.py` | MD write/delete/backfill for scripts & drafts (YAML frontmatter + body, idempotent) |
| `frameworks/api_routes.py` | /frameworks router — GET list/detail, PUT (validate YAML → write file + UPDATE DB), DELETE |
| `frameworks/instagram_frameworks/script_writer.py` | story_nodes × reel_frameworks → reel_scripts; calls md_mirror.write_script_md after insert |
| `content_writer/api_routes.py` | /content-writer — PATCH/DELETE draft + open-folder; mirrors on save |
| `content_writer/repository.py` | story_nodes / frameworks / drafts; `Framework.name = source_file or id` |
| `ideas/routes.py` | /ideas APIRouter — list/create/get/patch/delete + LinkedIn/Reel generate |
| `frontend/src/App.jsx` | Tab router — 6 tabs including Frameworks |
| `frontend/src/components/FrameworksTab.jsx` | Master/detail YAML editor — title/description fields patch `source_file`/`description` in YAML |
| `frontend/src/components/ReelWriter.jsx` / `ContentWriter.jsx` | Editable textarea canvas, folder/save/delete buttons, dropdowns show `source_file — meta` |
| `frontend/src/frameworksApi.js` | fetchFrameworksList/Framework, putFramework, deleteFramework |

## Edit Here When...
| Change | File |
|--------|------|
| Add/rename sidebar tabs | `Sidebar.jsx` + `App.jsx` |
| Framework CRUD endpoints | `frameworks/api_routes.py` |
| Script/draft MD format or path | `shared/shared/md_mirror.py` + `[md_mirror]` in `config.toml` |
| Dropdown label format | `ReelWriter.jsx` / `ContentWriter.jsx` framework `<select>` option block |
| Framework display title | Frameworks tab → TITLE field (writes `source_file` in YAML + DB) |
| LinkedIn / Reel generation model | `config.toml` → `[content_writer]` / `[script_writer] ollama_model` |
| Design tokens / glass styles | `frontend/tailwind.config.js` + `frontend/src/index.css` |

## Active Context
- **Done:** v1.9 — MD mirror utility + startup backfill; Reels/ContentWriter inline edit/delete/open-folder; Frameworks tab with editable title (source_file) / description / full YAML; all 17 framework titles renamed intelligently (e.g. "Career Thesis -> 5 Lessons + Anecdote", "90-Day Python Roadmap (Free)"); dropdowns in both writers now show `source_file — hook_type · pacing/tone · cta`.
- **Next:** Optional — purge stale `ref1-instagram-contrarian-v1` DB row whose YAML was deleted; consider custom dropdown component to render multi-line option (title + subtitle).
- **Notes:** `scripts/` and `drafts/` are gitignored MD mirrors. Framework PUT validates YAML before touching disk. Both `frameworks` (LinkedIn) and `reel_frameworks` (Reels) tables share the same router, dispatched on `channel` path param.
