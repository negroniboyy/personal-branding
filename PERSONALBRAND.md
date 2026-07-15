# Personal Brand (PBS) — Agent Guide

Start here. This is the stable architecture map for the `personal_brand` repo — Max's
content decision system. It is this repo's equivalent of
`OpenMontage/OpenMontage/AGENT_GUIDE.md`: read it before acting, then follow pointers
to the live/detail docs rather than re-deriving context from scratch.

**Doc roles:** this file = the *stable map* (architecture, file roles, conventions).
`../md/checkpoint.md` at the BrandStudio root = the *live pointer* (what's true right
now). `README.md` = the *ops manual* (machines, deploys, disaster recovery). For
anything time-sensitive, checkpoint wins over this file.

## First Interaction — Session Bootstrap

Follow the root `CLAUDE.md` §0: read **`../md/checkpoint.md`** and
**`../md/code_index.md`** at the **BrandStudio root** (one level up). This repo's own
`md/` directory is retired — pointer stubs only, never read or write it. Notify the
user briefly once loaded.

## What PBS Is (v3 architecture, live since 2026-07)

PBS turns ideas into voice-matched content and puts a human decision gate in front of
everything that ships. It is **not** a video production tool — approved reel scripts
hand off to **OpenMontage** (see below).

```
Notion CONTENT DB  ◀──two-way sync──▶  ideas (SQLite, VM)
        ideas → framework picker (LLM) → tiered generation (OpenRouter)
              → content_drafts (LinkedIn) / reel_scripts (versioned reels)
        → Studio review: approve / kill + verdict note (feeds future prompts)
        → caption + CTA → posted   (status pushed back to Notion)
        → approved reel script → OpenMontage (manual handoff, video production)
```

Key v3 facts (things that CHANGED from the retired v2 — do not trust old docs):

- **Ideas come from Notion**, synced two ways (`notion_ideas/`): Notion wins on
  content, PBS wins on lifecycle status. There is **no diary pipeline, no
  story_nodes, no narrative warehouse** — all archived under `_archive/`.
- **All LLM calls go through OpenRouter** (`config/openrouter_models.yaml` routes
  per-task, primary + fallback, no silent model swap). **No Ollama.**
- **Reel scripts are tiered and versioned**: tiers `raw` / `beat-edit` / `scripted`
  (templates in `frameworks/instagram_frameworks/prompts/script_writer_{raw,beat,idea}.txt`),
  regeneration creates v2/v3… in one version family; the "live" version drives status.
- **Generation is asynchronous**: every generate/sync/scan runs as a job in the
  SQLite-backed queue (`jobs/`), executed by a worker thread inside the API process.
  The frontend polls via `frontend/src/lib/useJob.js`.
- **Deployment is two-machine** (v4 Phase 0): the API + DB run 24/7 on the `maxlab`
  GCP VM; the Mac runs the frontend and heavy extraction, pushing results to the VM
  over Tailscale. Full ops detail: `README.md`.

**Current goal (v4 masterplan, `handoff/blueprint_v4.0_masterplan.md`):** stop
building, start shipping. Phases gate on posted content: B at 5 posts, C at 15, D
at 30. No new feature work unless the user asks.

## Stack

Python 3.12 · `uv` · FastAPI (:9000) · SQLite · React 18 · Vite · Tailwind.
Local dev: `./start.sh` (2 tabs) or see `README.md` §3. Production: systemd on the VM.

## Reading Order

1. Root `CLAUDE.md` (BrandStudio) — guardrails: model routing, blueprint protocol. **Always in force.**
2. `../md/checkpoint.md` — what's true right now.
3. This file — stable map.
4. `../md/code_index.md` — file → role / key symbols, per subsystem.
5. `brandguide/` — **mandatory** before writing or reviewing any generation prompt.

## Pipeline Stages & Canonical Artifacts

| Stage | What happens | Canonical output | Key files |
|---|---|---|---|
| **Sync** | Notion CONTENT DB ⇄ local ideas (nightly on VM + on-demand button) | `ideas` rows | `notion_ideas/sync.py`, `mapper.py` |
| **Generate** | Idea → framework pick → tiered, voice-injected draft/script (async job) | `content_drafts` / `reel_scripts` rows | `ideas/routes.py`, `frameworks/picker.py`, `frameworks/instagram_frameworks/script_writer.py`, `content_writer/service.py`, `jobs/handlers.py` |
| **Review** | Human approves/kills with verdict note; verdicts feed future prompts | `status`, `verdict_note` | `shared/shared/lifecycle.py`, `frontend/src/components/StudioTab.jsx` |
| **Package** | Caption + CTA generated (gated until approved) | `caption`, `cta` | `shared/shared/lifecycle.py` (`CAPTION_PROMPT`) |
| **Post** | Marked posted; status pushed back to Notion | `posted_at` + Notion status | `notion_ideas/sync.py::push_status` |
| **Extract** (side channel) | Reference MP4 → framework (talking-head via Whisper, beat-edit via vision). **Mac-only**, pushes to VM | `reel_frameworks` rows | `frameworks/instagram_frameworks/extract_reel.py` (`PBS_API_BASE`, `--beat-edit`), `POST /frameworks/reel/ingest` |
| **Produce** (external) | Approved reel script becomes a video | OpenMontage project | See "Relationship to OpenMontage" |

## Directory Index

| Path | Role |
|---|---|
| `NOTION DIARY FETCHER/` | FastAPI backend root (name is historical). `api/main.py` mounts all routers on :9000 + runs migrations and the jobs worker at startup; `api/reel_routes.py` (reel versioning); `config.toml`; `data/notion_diary.db` (**production copy lives on the VM**); `.env` (secrets, never in git) |
| `frontend/` | React 18 + Vite UI. `src/apiBase.js` reads `VITE_API_BASE`; `src/App.jsx` owns tab state; `src/lib/useJob.js` is the job-polling hook every generation surface uses |
| `ideas/` | `/ideas` router — CRUD + idea-linked generation. **The primary surface.** `repository.py` derives idea status from linked drafts/reels (live-version aware) |
| `notion_ideas/` | Two-way Notion sync — `sync.py` (pull/push), `mapper.py` (field mapping), `config.py` |
| `content_writer/` | LinkedIn draft service — `service.py`, `prompt_builder.py` (voice-injected), `repository.py`, `recommender.py` |
| `frameworks/` | `api_routes.py` (framework CRUD + outcome stats + `/reel/ingest`), `picker.py` (LLM picker, `video_format`-aware, keyword fallback) |
| `frameworks/instagram_frameworks/` | `script_writer.py` (TIER_TEMPLATES, versioned `save_script`), `extract_reel.py` (Mac-only extraction), `llm_client.py` (**`complete()` returns a `(content, model_used)` tuple**), `prompts/`, `references/` (gitignored MP4s) |
| `frameworks/linkedin_frameworks/` | LinkedIn framework storage (`frameworks/`, `schema.yaml`); its extractor is archived |
| `jobs/` | Background job queue — `queue.py` (persistence, worker, crash recovery, `register()`), `handlers.py` (all job kinds), `routes.py` |
| `openrouter/` | `router.py` (cascade primary → secondary, returns actual model, no silent swap), `client.py` |
| `config/` | `openrouter_models.yaml` — single source of truth for model routing per task |
| `shared/shared/` | `lifecycle.py` (STATUSES, CAPTION_PROMPT, `get_feedback_block` — source of truth for the review lifecycle), `md_mirror.py`, `logger.py`. Installed as the `shared` package |
| `brandguide/` | **The voice/taste layer** — see next section |
| `deploy/` | Ops assets: systemd units, nightly script, Mac backup-pull, launchd plist (see `README.md`) |
| `handoff/` | Blueprints (PRDs): `blueprint_v3.0`–`v3.4` (v3 trail), `blueprint_v4.0_masterplan.md` (**current roadmap**), `insight_helper_workflow.md` (idea top-up skill) |
| `scripts/` · `drafts/` | Human-readable `.md` mirrors of generated reel scripts / LinkedIn drafts (`md_mirror.py`). DB is the source of truth |
| `knowledge_base/` · `memory/` | Reference creator summaries / cross-session notes (`memory/glossary.md` = decoder ring). Low-traffic; `knowledge_base/` is slated for archive |
| `md/` | **RETIRED** — pointer stubs to the root `../md/`. Never read or write |
| `_archive/` | All retired v2 code: diary sync, narrative warehouse, story-first UI, Ollama client, LinkedIn extractor, batch CLIs. Archive-don't-delete policy — but never build on it |

## The Brandguide Layer (Voice & Taste — Read Before Generating)

Nothing should be generated or reviewed without this context loaded:

| File | Role |
|---|---|
| `brandguide/voice_dna.md` | Voice source of truth — sentence rhythm, who's speaking, tone rules |
| `brandguide/voice_dna_block.txt` | **Shared voice kit** injected into every generation prompt (reels + LinkedIn). Single source of truth — edit here, never per-prompt |
| `brandguide/brandbook.md` | Positioning, audience, and the production time caps |
| `brandguide/reference_analysis_reference1.md` | Worked analysis of a reference creator |

**Rule of thumb:** tune voice/craft moves → `voice_dna_block.txt`. Tune reel output
format per tier → `prompts/script_writer_{raw,beat,idea}.txt`. Don't duplicate voice
text across prompt files.

## Edit-Here-When Table

| Change | File |
|---|---|
| v4 roadmap / phases / gates | `handoff/blueprint_v4.0_masterplan.md` |
| Add/change model for a task | `config/openrouter_models.yaml` |
| Reel tier templates | `frameworks/instagram_frameworks/prompts/script_writer_{idea,raw,beat}.txt` |
| Reel version-family logic | `jobs/handlers.py::_handle_generate_reel`, `NOTION DIARY FETCHER/api/reel_routes.py` |
| Notion ideas sync (pull/push/mapping) | `notion_ideas/` |
| Add a background job kind | `jobs/handlers.py` + `jobs/queue.py` `register()` |
| Tune voice / craft moves | `brandguide/voice_dna_block.txt` |
| Lifecycle statuses / caption prompt / feedback | `shared/shared/lifecycle.py` |
| Beat-edit extraction prompt/logic | `extract_reel.py::process_beat_edit_file`, `prompts/extract_reel_beat.txt` |
| Ops (units, backups, recovery) | `deploy/` + `README.md` |
| Video pipeline / render / TTS / avatar | **Not here** — `OpenMontage/OpenMontage/AGENT_GUIDE.md` first, mandatory |

## Conventions

- **Blueprint Protocol:** non-trivial features get `handoff/blueprint_v[X.X]_[feature].md`
  before code — state, logic, specs, Definition of Done (root `CLAUDE.md` §2).
- **Live docs, not append-only:** root `../md/checkpoint.md` / `code_index.md` are
  edited in place via `/session-checkpoint`, never appended to.
- **Business logic stays out of UI files** — React components call `src/*Api.js`
  wrappers; new generation surfaces wire through `jobs.queue.enqueue` + `useJob`.
- **MD mirroring:** generated scripts/drafts mirror to `scripts/`/`drafts/` as dated
  `.md` files; the DB is the source of truth.
- **No silent fallback masking:** the OpenRouter cascade surfaces which model actually
  ran; a failing selected model is an error, not a hidden swap.
- **Gotcha:** `llm_client.complete()` / `complete_vision()` return a
  **`(content, model_used)` tuple** — callers must unpack.
- **Heavy deps are Mac-only:** whisper/scenedetect live in the `extraction` extra
  (`uv sync --extra extraction` locally; plain `uv sync` on the VM).
- **Sandbox constraint:** OpenRouter is blocked in agent sandboxes — real generation
  runs on Max's machines only.

## Relationship to OpenMontage

Two repos, two layers, manual handoff:

- **PBS** owns the *content decision layer* — what story, what voice, which platform,
  and whether it's good enough to ship (Studio verdict loop).
- **OpenMontage** (`OpenMontage/OpenMontage/`) owns the *production layer* — turning an
  approved script into a video via its pipeline system (Rule Zero: all production goes
  through a pipeline, never ad-hoc tool calls).

**Max's actual workflow** (`OpenMontage/OpenMontage/MY_WORKFLOW.md`): shoot + cut in
DaVinci Resolve → draft MP4 into OpenMontage → generate assets (overlays, subtitles,
visuals, localizations) via the Hybrid pipeline → back into DaVinci for final polish.

**Handoff points:**
1. A `reel_scripts` row reaches `approved` in Studio → its script text + verdict notes
   + `brandguide/voice_dna.md` become the brief for an OpenMontage run.
2. Brandguide files are the right inputs to OpenMontage's brand-voice workflows —
   feed them, not generic prompts.
3. The handoff is **manual today**. v4 Phase A plans a brief-compiler file handoff
   (still human-triggered). If automating further, that's a blueprint, not an ad-hoc
   script.

When a task is actually about video production, switch context: read
`OpenMontage/OpenMontage/AGENT_GUIDE.md` **before responding** — it routes your first
action. OpenMontage runs on the Mac only; the VM never touches video.

## Quick Lookup

| Question | Where to look |
|---|---|
| What's true right now (status, blockers, next)? | `../md/checkpoint.md` (BrandStudio root) |
| What does this file/module do? | `../md/code_index.md`, or the Directory Index above |
| How do I run / deploy / recover this? | `README.md` |
| How should generated content sound? | `brandguide/voice_dna.md` + `voice_dna_block.txt` |
| What's the roadmap and what's gated? | `handoff/blueprint_v4.0_masterplan.md` |
| How was feature X designed? | `handoff/blueprint_v[X.X]_[feature].md` |
| A term/tool I don't recognize? | `memory/glossary.md` |
| How do I turn an approved script into a video? | `OpenMontage/OpenMontage/MY_WORKFLOW.md` |
| Out of content ideas? | `/insight-helper` skill (`handoff/insight_helper_workflow.md`) |

## What Not To Do

- Don't generate or judge content without loading `brandguide/` voice context first.
- Don't read or write this repo's `md/` — the live docs are at the BrandStudio root.
- Don't build on anything in `_archive/` — it's retired v2 code kept for reference.
- Don't duplicate voice/tone text into prompt files — route through `voice_dna_block.txt`.
- Don't build video-production logic inside PBS — hand off to OpenMontage.
- Don't run `uv sync --extra extraction` on the VM (disk can't fit torch), and don't
  expect extraction/scan to work on the VM at all — it's a Mac-side CLI act.
- Don't skip the Blueprint Protocol for non-trivial features.
- Don't treat this file as live state — `../md/checkpoint.md` wins.
