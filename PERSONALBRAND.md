# Personal Brand — Agent Guide

> ⚠️ **v3 REBOOT PENDING (2026-07-03):** the diary→warehouse→story-first pipeline described below is being retired — see `handoff/blueprint_v3.0_pbs_reboot.md` (the PRD) and `md/checkpoint.md` before trusting any Ingest/Extract/story-first section here. Brandguide references remain valid (rebuilt same day). This file gets rewritten after v3 implementation lands.

Start here. This is the complete operating guide and index for the `personal_brand` repo — Max's content creation system. It is the `personal_brand` equivalent of `OpenMontage/OpenMontage/AGENT_GUIDE.md`: read this before acting, then follow the pointers to the live/detail docs rather than re-deriving context from scratch.

## First Interaction — Session Bootstrap

Before anything else, follow `CLAUDE.md` §0: read `md/checkpoint.md` (live session state) and `md/code_index.md` if present (file → role index). These are **live documents**, updated via `/session-checkpoint` — never stale summaries baked into this file. Notify the user briefly once loaded.

This file (`PERSONALBRAND.md`) is the **stable map** — architecture, pipeline, file roles, conventions. `md/checkpoint.md` is the **live pointer** — what's true right now, what changed last session, what's next. Read both; trust checkpoint.md over this file for anything time-sensitive (current version, active blockers, pending ops).

## What Personal Brand Is

Personal Brand is Max's end-to-end content pipeline: raw life material (Notion diary entries) → scored, structured story material → voice-aware LinkedIn/Instagram drafts → human review → posted content. It is **not** a video production tool — for that, it hands off to **OpenMontage** (see "Relationship to OpenMontage" below).

```
Notion Diary → Stage1 Extractor (LLM) → story_nodes (SQLite, scored/tagged)
  → Studio / Writer / Reels UI (voice-aware generation via OpenRouter/Ollama)
  → human review (approve/kill + verdict) → caption+CTA → posted
  → (optional) OpenMontage: turn an approved reel script into a produced video asset
```

Core loop, daily: open **Studio** tab → review queue → approve/kill (with a verdict note — it feeds future prompts) → on approval, generate Caption+CTA → mark posted. A nightly routine tops up the queue and mirrors approved items to Asana.

**Primary goal (UAT phase, per checkpoint):** stop building, start shipping — get 30 pieces generated/approved/posted. The system is considered built; the current job is execution, not further feature work, unless the user asks for it.

## Stack

Python 3.12 · `uv` · FastAPI (port 9000) · SQLite · React 18 · Vite · Tailwind v3.4. Run via `./start.sh` (opens 2 terminal tabs: API + frontend). See `README.md` for manual quickstart commands.

## Reading Order

1. `CLAUDE.md` — root guardrails: model routing, blueprint protocol, sub-agent pre-flight, context management. **Always in force.**
2. `md/checkpoint.md` — what's true right now (status, file map deltas, next steps, constraints).
3. This file (`PERSONALBRAND.md`) — stable architecture map and index.
4. The relevant subsystem doc from the tables below — know *how* before touching a subsystem.
5. `brandguide/` — the taste/voice layer — **mandatory** before writing or reviewing any generation prompt.

## Model Routing (from `CLAUDE.md`)

| Phase | Model | Directive |
|---|---|---|
| Planning | Opus 4.7 | Build a Blueprint (`handoff/blueprint_v[X.X]_[feature].md`); no code until alignment |
| Execution | Sonnet | Zero verbosity; code/diffs only |
| Testing/Scout | Haiku | Validate results, fetch data/files |

Announce every model switch to the user. Announce every time a CLAUDE.md protocol (blueprint, sub-agent pre-flight, checkpoint trigger) is being followed.

## Pipeline Stages & Canonical Artifacts

| Stage | What happens | Canonical output | Key files |
|---|---|---|---|
| **Ingest** | Notion diary synced locally | `notion_diary.db` rows | `NOTION DIARY FETCHER/src/notion_fetcher`, `uv run sync` |
| **Extract** | LLM extracts story_nodes from diary pages, dedups, scores | `story_nodes` (SQLite) | `narrative_warehouse/stage1_extractor.py`, `stage2_synthesizer.py`, `normalizer.py` |
| **Generate** | Voice-aware LinkedIn/Reel draft generation (freeform idea path or story-first path) | `content_drafts` / `reel_scripts` rows | `content_writer/prompt_builder.py`, `frameworks/instagram_frameworks/script_writer.py`, `ideas/routes.py` |
| **Review (lifecycle)** | Human approves/kills with verdict; verdict feeds back into future prompts | `status`, `verdict`, `verdict_note` columns | `shared/shared/lifecycle.py`, `frontend/src/components/StudioTab.jsx` |
| **Package** | Caption + CTA generated (gated until approved) | `caption`, `cta` | `shared/shared/lifecycle.py` (`CAPTION_PROMPT`) |
| **Post** | Marked posted; mirrored to Asana Content calendar | `posted_at`, `asana_task_gid` | Nightly Cowork routine, `handoff/routine_nightly_content.md` |
| **(Optional) Produce** | Approved reel script becomes a video asset | OpenMontage project under `projects/<name>/` | See "Relationship to OpenMontage" |

Batch/one-off generation utilities: `batch_generate.py` (rotates unused story_nodes across N frameworks), `gen_one_node.py` (one node × all frameworks, bypasses an int-typed CLI bug — use text `--story-id`), `migrate_backfill_processed.py` (one-time backfill).

## Directory Index

| Path | Role |
|---|---|
| `NOTION DIARY FETCHER/` | FastAPI backend root — `api/main.py` mounts all routers on :9000; `config.toml` is the single config source (subsystem `provider = openrouter\|ollama`); `src/notion_fetcher` is the sync client; `data/notion_diary.db` is the live SQLite DB |
| `frontend/` | React 18 + Vite + Tailwind UI. `src/apiBase.js` centralizes the API origin (`VITE_API_BASE` env, falls back to `:9000`). `src/App.jsx` owns tab state + deep-link handoff between tabs. |
| `frontend/src/components/` | `StudioTab.jsx` (home — backlog meter, queue, approve/kill/caption/post), `ReelWriter.jsx` / `ContentWriter.jsx` (per-channel generation UIs), `IdeasTab.jsx`/`IdeaDetail.jsx` (freeform idea generation), `StoryNodeList.jsx`/`StoryNodeCard.jsx`/`StoryPreview.jsx` (Warehouse browsing), `FrameworksTab.jsx`, `NarrativeDashboard.jsx`, `ModelSelector.jsx` |
| `narrative_warehouse/` | Diary → story_nodes pipeline. `stage1_extractor.py` (extraction + dedup guard), `stage2_synthesizer.py`, `normalizer.py`, `db.py`, `config.py`. Has its own `tests/`. |
| `frameworks/instagram_frameworks/` | Reel generation. `script_writer.py` (story-first + freeform builders, romantic-content filter, story rotation), `llm_client.py` (`complete()` → `(content, model_used)`), `prompts/script_writer.txt` (story-first) and `prompts/script_writer_idea.txt` (idea-tuned), `extract_reel.py` (reference-reel framework extraction), `frameworks/`, `references/` |
| `frameworks/linkedin_frameworks/` | LinkedIn equivalent of the above — `extract_linkedin.py`, `llm_client.py`, `schema.yaml`, `frameworks/`, `prompts/`, `references/` |
| `content_writer/` | LinkedIn draft generation service — `prompt_builder.py` (`build_freeform_prompt`, voice+CTA filtering), `service.py`, `db.py`, `models.py`, `repository.py`, `recommender.py`, `api_routes.py` |
| `ideas/` | `/ideas` router — CRUD + `generate_linkedin`/`generate_reel`, calling the voice-aware freeform builders in `content_writer`/`frameworks` |
| `shared/shared/` | Cross-cutting: `lifecycle.py` (STATUSES, status migrations, `CAPTION_PROMPT`, `get_feedback_block` — the source of truth for the review/post lifecycle), `md_mirror.py`, `logger.py` |
| `openrouter/` | `router.py` (cascade: primary → secondary → ollama, returns actual model used, no silent fallback masking), `client.py` (OpenAI-SDK wrapper, retry + SSE) |
| `config/` | `openrouter_models.yaml` — single source of truth for model routing per task |
| `brandguide/` | **The taste/voice layer.** See dedicated section below. |
| `handoff/` | Blueprints (`blueprint_v[X.X]_[feature].md`) — one per planned feature, per the CLAUDE.md Blueprint Protocol. `routine_nightly_content.md` is the canonical mirror of the Cowork nightly-routine prompt — edit here, then push to the scheduled task. |
| `knowledge_base/` | Reference creator summaries, title/script pattern libraries used to seed frameworks (`eliasmaman.*`, `titulos_seguidores.*`, `script_templates.json`, `title_patterns.json`, `knowledge_registry.json`) |
| `memory/` | Cross-session memory: `glossary.md` (decoder ring for terms/tools), `reference_creators.md` (style profiles of creators Max studies), `projects/personal_brand_system.md` (system-level project memory) |
| `scripts/` | Generated reel script `.md` mirrors, one file per script, named `<date>_reel-<n>_<framework>-v<version>.md` |
| `drafts/` | Generated LinkedIn draft `.md` mirrors (same mirroring pattern as `scripts/`) |
| `content assets/` | Static image assets used in content pieces |
| `logs/` | Rotating logs per subsystem (`narrative_warehouse`, `frameworks_api`, `md_mirror`, `instagram_frameworks`) |
| `md/` | **Live session documents** — `checkpoint.md` (state) and `code_index.md` (file index), maintained via `/session-checkpoint`. Read first, edit in place, never append. |
| `docs/` | Misc reference docs (`superpowers/specs`) |

## The Brandguide Layer (Voice & Taste — Read Before Generating)

`brandguide/` is the control centre for *what makes content sound like Max* and *what's working*. Nothing should be generated or reviewed without this context loaded:

| File | Role |
|---|---|
| `brandguide/voice_dna.md` | Voice source of truth — sentence rhythm, who's speaking, tone rules. Distilled inline into `prompts/script_writer.txt` for the story-first path. |
| `brandguide/voice_dna_block.txt` | **Shared voice kit** (VOICE DNA + 6 craft moves + transformation example) — injected into both idea-path freeform builders (`script_writer_idea.txt` for reels, `prompt_builder.py` for LinkedIn). Single source of truth — edit here, not per-prompt. |
| `brandguide/brandbook.md` | Overall positioning: identity-first, data-informed, reflective, structured, in-progress. Core audience definition. |
| `brandguide/linkedin.md` | LinkedIn-specific positioning and tone (curious not authoritative, reflective not motivational). |
| `brandguide/content_workflow.md` | The production SOP and its **non-negotiable time caps** (30 min planning / 5 min draft gen / 20 min review / 5 min image gen). |
| `brandguide/production_playbook.md` | UI-based weekly production loop for the Reel tab specifically, plus Definition of Done. |
| `brandguide/content_strategy_log.md` | **Living strategist log** — per-node verdicts, which frameworks fit which voice patterns, what's been learned. Update after every generation/review pass. |
| `brandguide/campaign_01_builder_in_public.md` | Active campaign brief (niche-discovery arc) — read when planning content batches, not one-off pieces. |

**Rule of thumb:** tune voice/craft moves → edit `voice_dna_block.txt`. Tune reel output format → `prompts/script_writer.txt`. Log a finding/verdict → `content_strategy_log.md`. Don't duplicate voice text across prompt files — everything routes through the shared block.

## Edit-Here-When Table

| Change | File |
|---|---|
| Add/change model for a task | `config/openrouter_models.yaml` |
| Switch subsystem provider (cloud ↔ local) | `NOTION DIARY FETCHER/config.toml` — `provider` under the relevant subsystem |
| Adjust the romantic-content filter | `frameworks/instagram_frameworks/script_writer.py` → `ROMANTIC_TAGS` + `_romantic_words` |
| Change reel script output format | `frameworks/instagram_frameworks/prompts/script_writer.txt` |
| Tune voice / craft moves (both idea paths) | `brandguide/voice_dna_block.txt` |
| Reel/LinkedIn generation logic | `frameworks/instagram_frameworks/script_writer.py` / `content_writer/prompt_builder.py` |
| Stage1 dedup / skip logic | `narrative_warehouse/stage1_extractor.py` |
| Batch generation defaults | `batch_generate.py` → `run()` argparse defaults |
| Lifecycle statuses / caption prompt / feedback loop | `shared/shared/lifecycle.py` |
| Log a voice/framework finding or verdict | `brandguide/content_strategy_log.md` |
| Nightly routine behavior | `handoff/routine_nightly_content.md`, then sync to the Cowork scheduled task |

## Conventions

- **Blueprint Protocol:** any non-trivial feature gets `handoff/blueprint_v[X.X]_[feature].md` before code — state, logic, specs, Definition of Done. See `CLAUDE.md` §2.
- **Live docs, not append-only:** `md/checkpoint.md` and `md/code_index.md` are edited in place via `/session-checkpoint`, never appended to.
- **Business logic stays out of UI files** — React components call into `frontend/src/*Api.js` wrappers; no direct fetch scattered in components.
- **MD mirroring:** every generated script/draft gets mirrored to `scripts/` or `drafts/` as a dated `.md` file (`shared/shared/md_mirror.py`) — the DB is the source of truth, the `.md` mirror is for human/grep-friendly review.
- **No silent fallback masking:** `openrouter/router.py` cascades primary → secondary → ollama, but a failing selected model surfaces as an error, not a silently swapped model. Same spirit as OpenMontage's "no silent runtime swap" rule.
- **Sandbox constraint:** OpenRouter is blocked behind a SOCKS proxy in the sandbox — all real generation runs on Max's machine, not in an agent sandbox.

## Relationship to OpenMontage

Personal Brand and OpenMontage are separate repos designed to run in parallel and hand off to each other:

- **Personal Brand** owns the *content decision layer* — what story to tell, in what voice, for which platform, and whether it's good enough to ship (Studio review/verdict loop).
- **OpenMontage** (`OpenMontage/OpenMontage/`) owns the *production layer* — turning an approved script/idea into an actual video asset, via its pipeline system (see `OpenMontage/OpenMontage/AGENT_GUIDE.md`, Rule Zero: all production goes through a pipeline, never ad-hoc tool calls).

**Max's actual OpenMontage workflow** (`OpenMontage/OpenMontage/MY_WORKFLOW.md`): shoot and cut in DaVinci Resolve → bring the draft MP4 into OpenMontage → generate assets (text overlays, subtitles, visuals, localizations) via the **Hybrid pipeline** (`pipeline_defs/hybrid.yaml`) → bring assets back into DaVinci for final fine-tuning. Reference-reel analysis (transcript, pacing, cut rhythm) and brand-voice-brainstorm (reference + Personal Brand's `brandguide/` as the brief) are both first-class OpenMontage entry points that should be fed by Personal Brand's voice/brand docs, not generic prompts.

**Practical handoff points:**
1. A `reel_scripts` row reaches `status = approved` in Personal Brand's Studio → its script text + verdict notes become the brief for an OpenMontage `hybrid` or `talking-head` pipeline run.
2. `brandguide/voice_dna.md` / `voice_dna_block.txt` / `brandguide/campaign_01_builder_in_public.md` are the right inputs to OpenMontage's "Brand Voice Brainstorm" workflow when asking it to adapt a reference reel to Max's voice.
3. Nothing in Personal Brand currently automates this handoff — it's manual today (copy script/brief into an OpenMontage session). If automating becomes worthwhile, it belongs in a `handoff/blueprint_v[X.X]_openmontage_bridge.md` per the Blueprint Protocol, not as an ad-hoc script.

Do not duplicate OpenMontage's pipeline/tool docs here — when a task is actually about video production (pipelines, render runtimes, Layer 3 vendor skills), switch context and follow `OpenMontage/OpenMontage/AGENT_GUIDE.md` instead.

## Quick Lookup

| Question | Where to look |
|---|---|
| What's true right now (status, blockers, next steps)? | `md/checkpoint.md` |
| What does this file/module do? | This file's Directory Index, or `md/code_index.md` |
| How should generated content sound? | `brandguide/voice_dna.md` + `voice_dna_block.txt` |
| Is this content good? What's worked before? | `brandguide/content_strategy_log.md` |
| What's the weekly production loop? | `brandguide/production_playbook.md` (reels), `brandguide/content_workflow.md` (general) |
| How do I run this locally? | `README.md` |
| What's a term/tool I don't recognize? | `memory/glossary.md` |
| How do I turn an approved script into a video? | `OpenMontage/OpenMontage/MY_WORKFLOW.md` (this repo's "Relationship to OpenMontage" section is the bridge) |
| Where does a planned feature's design live? | `handoff/blueprint_v[X.X]_[feature].md` |

## What Not To Do

- Don't generate or judge content without loading `brandguide/` voice context first.
- Don't hand-edit `md/checkpoint.md` into an append log — it's a live snapshot, keep it current in place.
- Don't duplicate voice/tone text into a new prompt file — route through `brandguide/voice_dna_block.txt`.
- Don't build video-production logic inside Personal Brand — that's OpenMontage's job; hand off instead.
- Don't skip the Blueprint Protocol for non-trivial features — planning model builds the blueprint, execution model implements it.
- Don't treat this file as live state — for current status/blockers, `md/checkpoint.md` wins.
