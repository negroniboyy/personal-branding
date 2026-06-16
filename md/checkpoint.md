# Personal Brand Monorepo — 2026-06-12

**Stack:** Python 3.12 · uv · FastAPI · SQLite · React 18 · Vite · Tailwind v3.4 · **Run:** `./start.sh` (2 tabs) · **v2.6**

## Status
v2.6: content lifecycle shipped. Both `reel_scripts` + `content_drafts` carry `status` (queued→approved→recorded→posted | killed), `verdict`/`verdict_note` (fed back into generation prompts), `caption`/`cta`, `asana_task_gid`, `posted_at`. New **Studio** tab = default home (pipeline queue, backlog meter X/30, approve/kill/package/post actions). Caption+CTA endpoint gated: 409 until reviewed (approved+). Cowork scheduled task `nightly-content-pipeline` (daily 06:30, runs while Cowork open): queue top-up via batch_generate, Asana "Content calendar" sync (project 1214297039839658, section Content-in-progress 1214297039839678), morning digest LOCKED until 30 approved posts. Blueprint: `handoff/blueprint_v2.6_content_lifecycle.md`; routine prompt mirror: `handoff/routine_nightly_content.md`.
v2.5: API moved 8000→9000; frontend origin centralized in `frontend/src/apiBase.js` (`VITE_API_BASE`). Reel model selection now honored end-to-end (local Ollama verified). Entering UAT — shipping content for a month.
v2.4: frontend UX overhaul. Global story threshold 0.80 + limit 200 shared across Writer/Reels/Warehouse. Framework dropdowns show DB tag. Warehouse cards deep-link to writers (story preselected + StoryPreview). Synthesize-week under ADVANCED. Backend `story_node_id`/`framework_id` retyped int→str.
v2.3: story-first reel scripting, romantic-content filter, real model tracking, stage1 dedup guard. Two generators: `batch_generate.py` (top-N stories × top-M frameworks) and `gen_one_node.py` (one node × all frameworks, for voice-DNA A/B review).

## File Map
| File | Role |
|------|------|
| `NOTION DIARY FETCHER/api/main.py` | FastAPI :9000 — mounts all routers |
| `frontend/src/apiBase.js` | Single API origin — `VITE_API_BASE` env or `http://localhost:9000` fallback; all frontend BASE imports here |
| `NOTION DIARY FETCHER/api/reel_routes.py` | /reels router — `/generate` + `/generate/stream` SSE |
| `NOTION DIARY FETCHER/config.toml` | All config — subsystem `provider = openrouter\|ollama` |
| `config/openrouter_models.yaml` | Model routing table — single source of truth |
| `openrouter/router.py` | Cascade: primary→secondary→ollama; returns actual model used |
| `openrouter/client.py` | OpenAI-SDK wrapper — retry + SSE streaming |
| `frameworks/instagram_frameworks/llm_client.py` | `complete()` → returns `(content, model_used)` tuple |
| `frameworks/instagram_frameworks/script_writer.py` | Reel script gen — romantic filter, clean_script_output, story-first |
| `frameworks/instagram_frameworks/prompts/script_writer.txt` | Story-first prompt — plain voiceover output, no scene labels |
| `narrative_warehouse/stage1_extractor.py` | Diary → story_nodes; Layer 2 dedup guard (skip if page_id exists) |
| `batch_generate.py` | Batch runner — `--stories N --frameworks N --dry-run` |
| `gen_one_node.py` | One node × ALL frameworks — `--story-id <text> --out f.json` (text IDs; bypasses int-typed CLI bug) |
| `migrate_backfill_processed.py` | One-time migration — marks 93 pages processed where story_node exists |
| `brandguide/content_strategy_log.md` | **Strategist control centre** — voice patterns, framework fit map, per-node verdict log |
| `brandguide/voice_dna.md` | Voice source of truth; distilled block lives inline in `prompts/script_writer.txt` |
| `brandguide/production_playbook.md` | UI-based weekly production SOP (Reel tab) + enrichment + DoD |
| `frontend/src/components/ReelWriter.jsx` | Reel tab UI — story+framework dropdowns, ONE per Generate click; StoryPreview panel, `initialStory` deep-link prop |
| `frontend/src/components/ContentWriter.jsx` | LinkedIn tab UI — same shape as ReelWriter; StoryPreview panel, `initialStory` deep-link prop |
| `frontend/src/components/StoryNodeList.jsx` | Warehouse list — auto ≥0.80, search/sort, SCORE badge (no manual filters); passes `onCreate` |
| `frontend/src/components/StoryNodeCard.jsx` | Compact expand-to-edit card; inline LinkedIn/Reel buttons → `onCreate(channel, node)` |
| `frontend/src/components/StoryPreview.jsx` | Shared STORY PREVIEW panel (score badge + user_state/conflict/outcome/bridge + tags) |
| `frontend/src/lib/frameworkLabel.js` | Dropdown label: `title (id) — meta`; reel uses source_file, linkedin uses name |
| `frontend/src/components/ModelSelector.jsx` | Provider/model dropdown — glass-panel, on-surface text (contrast fix) |
| `frontend/src/App.jsx` | Tab state + `handleCreate` deep-link (sets writer/reelStory, switches tab); default tab = studio |
| `shared/shared/lifecycle.py` | Lifecycle source of truth — STATUSES, migrate columns, update_meta, CAPTION_PROMPT, get_feedback_block |
| `frontend/src/components/StudioTab.jsx` | Studio home — backlog meter, QUEUE/IN PRODUCTION/SHIPPED, approve/kill/caption/post/verdict actions |
| `handoff/routine_nightly_content.md` | Canonical prompt for Cowork task `nightly-content-pipeline` (edit here, then update task) |

## Edit Here When...
| Change | File |
|--------|------|
| Add/change model for a task | `config/openrouter_models.yaml` |
| Adjust romantic content filter | `script_writer.py` → `ROMANTIC_TAGS` + `_romantic_words` |
| Change script output format | `prompts/script_writer.txt` |
| Switch subsystem provider (cloud↔local) | `config.toml` — change `provider` under subsystem |
| Reel/LinkedIn prompt logic | `frameworks/instagram_frameworks/script_writer.py` |
| Stage1 dedup / skip logic | `narrative_warehouse/stage1_extractor.py` |
| Batch generation defaults | `batch_generate.py` → `run()` argparse defaults |
| Log voice/framework findings, verdicts | `brandguide/content_strategy_log.md` |

## Active Context
- **Done (v2.4 frontend UX):** All 7 implementation tasks complete (global 0.80/200, frameworkLabel DB tag, ModelSelector contrast, Warehouse filter removal + compact cards + action buttons, Synthesize-week under Advanced, writer StoryPreview panels, deep-linking). Backend `story_node_id`/`framework_id` retyped int→str in `content_writer/{api_routes,models}.py`.
- **Verified:** `/narrative/story-nodes?min_score=0.8` returns total=87; `/content-writer/recommendations` returns 87. Screenshots confirmed Narrative tab (ADVANCED collapsible, SCORE ≥ 0.80 badge, no manual filters, populated story list) + Reels tab (frameworkLabel `title (id) — meta`, StoryPreview panel, visible ModelSelector).
- **NOT visually verified (preview-env limit, not a code defect):** Compact-card LinkedIn/Reel buttons rendering + the live deep-link click→writer flow. Preview tab runs offscreen → `requestAnimationFrame` paused → framer-motion `AnimatePresence mode="wait"` freezes mid-crossfade; DOM/snapshot read stuck frames. Code path verified by inspection (StoryNodeCard onCreate buttons + App.handleCreate). **Max should do the final click-through in a real focused browser.**
- **Done (prior):** BLANK SLATE — wiped all `reel_scripts` (39→0, autoincrement reset so next post = #1) to start clean on new prompt/models/frameworks. `content_drafts` empty, `ideas` (3) kept. Production playbook written. n=3 lessons retained in `content_strategy_log.md` (its verdict log now points at deleted script #s — references stale, lessons valid; left as-is per Max).
- **Finding (retained):** Voice layer GENERALIZES across themes. Dominant quality driver is **source-story concreteness, not framework** — rich source → clean; thin/abstract source → fabricated specifics (mitigate via IDEA HINT or enriching the node). Default frameworks: ref2-bold + ref1-contrarian. Weakest: ref1-bold_claim, ref6-bold (rambly, fabricate).
- **Next:** Daily loop = open Studio tab → review queue → approve/kill (+ verdict note: it feeds future prompts) → after approval hit Caption+CTA → mark posted. Nightly routine tops up queue + mirrors approved items to Asana Content calendar; digest unlocks at 30 approved. First routine run: click "Run now" once in Cowork Scheduled sidebar to pre-approve its tools. Pending: run `migrate_backfill_processed.py` once locally. v2.6 not yet committed to git (branch ideas-tab).
- **Reel model routing (FIXED + verified):** `/reels/generate` routes ALL providers through `openrouter.router.chat(override_model=body.model)` → `model_used` is always the real model; local `ollama:` ids run on-device. Confirmed: `ollama:gemma-32k:latest` runs locally and is recorded correctly in the MD. Was bugged: local picks fell into `generate_script()`→`llm_client.complete(section="script_writer")` which re-read config (provider=openrouter) and silently ran gpt-oss in the cloud. Output cleaned in both stream + non-stream paths. `override_model` has NO fallback — a failing model (e.g. `minimax/minimax-m2.5:free`, id unverified) surfaces as 500 instead of masking as gpt-oss.
- **Notes:** Framework UI titles are misleading source filenames — map: ref2-bold=`90-Day Python Roadmap (Free)`, ref1-contrarian=`reel_source`, ref3-pain=`Visibility Fear → Tolerance Pivot`, ref1-bold=`Storytelling Insight → 12-Beat Arc + DM`, ref6-bold=`3 Creator Mistakes → DM Lead-Gen`. `script_writer.py --story-id` is int-typed → use `gen_one_node.py`. Sandbox blocks OpenRouter (SOCKS) — generation must run on Max's machine.
- **Status:** UAT: user will test and generate some content for a month, taking notes of what can be improved and what would be nice to have. For now user has to start shipping things.
