# Personal Brand Monorepo — 2026-07-03

**Stack:** Python 3.12 · uv · FastAPI · SQLite · React 18 · Vite · Tailwind v3.4 · **Run:** `./start.sh` (2 tabs) · **v2.7 (v3.0 planned)**

## Status
PBS v3 reboot planned: PRD at `handoff/blueprint_v3.0_pbs_reboot.md` (awaiting approval). Retires diary/warehouse + Ollama; ingest becomes Notion two-way sync; ideas carry pillar + production tier. Brandguide rebuilt from scratch (brandbook v2, voice_dna v2). Code still on v2.7 until implementation lands.

## File Map
| File | Role |
|------|------|
| `handoff/blueprint_v3.0_pbs_reboot.md` | **The PRD** — v3 reboot spec, archive list, implementation order |
| `brandguide/brandbook.md` | Positioning source of truth v2 — 3 pillars, value prop, production tiers |
| `brandguide/voice_dna.md` | Voice source of truth v2 — 3 tier-registers, interview-derived |
| `brandguide/voice_dna_block.txt` | Voice injection kit v2 — shared by both idea-path builders |
| `NOTION DIARY FETCHER/api/main.py` | FastAPI :9000 — mounts all routers |
| `shared/shared/lifecycle.py` | Lifecycle source of truth — STATUSES, CAPTION_PROMPT, feedback block |
| `ideas/routes.py` | /ideas router — CRUD + `generate_linkedin`/`generate_reel` |
| `content_writer/prompt_builder.py` | LinkedIn idea-path builder — injects voice block + CTA filter |
| `frameworks/instagram_frameworks/script_writer.py` | Reel script gen (story-first + idea path) |
| `frontend/src/components/StudioTab.jsx` | Studio home — queue, approve/kill/caption/post |
| `config/openrouter_models.yaml` | Model routing — single source of truth |
| `PERSONALBRAND.md` | Repo agent guide — flagged stale pending v3 implementation |

## Edit Here When...
| Change | File |
|--------|------|
| Implementing v3 (any scope) | `handoff/blueprint_v3.0_pbs_reboot.md` (the spec) |
| Add/change model for a task | `config/openrouter_models.yaml` |
| Tune voice / register | `brandguide/voice_dna_block.txt` |
| Positioning / pillars | `brandguide/brandbook.md` |
| Reel/LinkedIn prompt logic | `frameworks/instagram_frameworks/script_writer.py`, `content_writer/prompt_builder.py` |
| Lifecycle statuses | `shared/shared/lifecycle.py` |
| Switch subsystem provider (until Ollama removed) | `NOTION DIARY FETCHER/config.toml` |

## Active Context
- **Done:** Brandguide rebuilt from scratch via interview (brandbook + voice_dna v2, old versions archived to `brandguide/_archive/`); profile written at `BrandStudio/profile/`; PRD `blueprint_v3.0_pbs_reboot.md` written.
- **Next:** Max approves the PRD → merge `ideas-tab` branch (first implementation step) → archive moves (warehouse, diary sync, Ollama) → Notion ideas sync.
- **Notes:** Repo still runs v2.7 code — diary/warehouse/Ollama not yet removed. Cowork nightly routine to be retired in favor of GCP VM scheduler. `migrate_backfill_processed.py` now moot (warehouse retiring).
