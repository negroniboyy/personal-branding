# Personal Brand Monorepo — 2026-06-16

**Stack:** Python 3.12 · uv · FastAPI · SQLite · React 18 · Vite · Tailwind v3.4 · **Run:** `./start.sh` (2 tabs) · **v2.7**

## Status
**PRIMARY GOAL (UAT):** stop building, start shipping — generate/approve **30 content pieces** in Studio and actually POST them. System is built; focus is execution now.
v2.7: voice-aware Ideas-tab generation. Both freeform builders now inject the creator's voice DNA + craft moves from shared `brandguide/voice_dna_block.txt` (single source of truth). Reel idea path uses new `prompts/script_writer_idea.txt` (idea-tuned: drops diary "select one thread" RULE 0). LinkedIn idea path filters CTA through voice (no "DM me"/"link in bio"). Same builders power Reels/Writer freeform modes → all 3 surfaces upgraded. Ideas tab UI: `App.jsx` widens container to `max-w-[1400px]` for ideas tab only (two-pane layout no longer clipped). Blueprint: `handoff/blueprint_v2.7_ideas_voice.md`.
v2.6: content lifecycle shipped. Both `reel_scripts` + `content_drafts` carry `status` (queued→approved→recorded→posted | killed), `verdict`/`verdict_note` (fed back into generation prompts), `caption`/`cta`, `asana_task_gid`, `posted_at`. New **Studio** tab = default home (pipeline queue, backlog meter X/30, approve/kill/package/post actions). Caption+CTA endpoint gated: 409 until reviewed (approved+). Cowork scheduled task `nightly-content-pipeline` (daily 06:30, runs while Cowork open): queue top-up via batch_generate, Asana "Content calendar" sync (project 1214297039839658, section Content-in-progress 1214297039839678), morning digest LOCKED until 30 approved posts. Blueprint: `handoff/blueprint_v2.6_content_lifecycle.md`; routine prompt mirror: `handoff/routine_nightly_content.md`.
v2.5: API moved 8000→9000; frontend origin centralized in `frontend/src/apiBase.js` (`VITE_API_BASE`). Reel model selection now honored end-to-end (local Ollama verified). Entering UAT — shipping content for a month.
v2.4: frontend UX overhaul. Global story threshold 0.80 + limit 200 shared across Writer/Reels/Warehouse. Framework dropdowns show DB tag. Warehouse deep-links. Backend `story_node_id`/`framework_id` retyped int→str.

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
| `frameworks/instagram_frameworks/script_writer.py` | Reel script gen — romantic filter, clean_script_output, story-first; `build_freeform_script_prompt` (idea path) now injects voice block via `script_writer_idea.txt`; `load_story_nodes(exclude_used_in=...)` rotation |
| `frameworks/instagram_frameworks/prompts/script_writer.txt` | Story-first (diary) reel prompt — voice DNA inline; verified path, untouched by v2.7 |
| `brandguide/voice_dna_block.txt` | **Shared voice kit** (VOICE DNA + 6 craft moves + transformation example) injected into both idea-path builders |
| `frameworks/instagram_frameworks/prompts/script_writer_idea.txt` | Idea-tuned reel prompt — voice block + framework; for already-refined ideas (no thread-selection) |
| `content_writer/prompt_builder.py` | LinkedIn prompts — `build_freeform_prompt` (idea path) now injects voice block + CTA voice filter |
| `ideas/routes.py` | /ideas router — CRUD + `generate_linkedin`/`generate_reel` (call the voice-aware freeform builders) |
| `narrative_warehouse/stage1_extractor.py` | Diary → story_nodes; Layer 2 dedup guard (skip if page_id exists) |
| `batch_generate.py` | Batch runner — `--stories N --frameworks N --dry-run`; rotates via `exclude_used_in="reel_scripts"`, falls back to top-N if all used |
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
| Tune the creator's voice / craft moves | `brandguide/voice_dna_block.txt` (shared by both idea paths) |
| Stage1 dedup / skip logic | `narrative_warehouse/stage1_extractor.py` |
| Batch generation defaults | `batch_generate.py` → `run()` argparse defaults |
| Log voice/framework findings, verdicts | `brandguide/content_strategy_log.md` |

## Active Context
- **FOCUS — ship the 30:** System is built; the job now is execution. Daily loop: open **Studio** → review queue → approve/kill (+verdict note: it feeds future prompts) → on approval hit **Caption+CTA** → mark **posted**. Nightly routine tops up queue + mirrors approved items to Asana Content calendar; morning digest unlocks at **30 approved**. As Max ships, capture "improve / nice-to-have" notes for the next build cycle.
- **Done (this session, v2.7):** Voice-aware idea generation (shared `voice_dna_block.txt`; `build_freeform_script_prompt` + `build_freeform_prompt` inject voice DNA/craft moves; new `script_writer_idea.txt`; LinkedIn CTA voice-filtered). Ideas-tab width fix in `App.jsx`. Both builders unit-verified (voice block + banned-phrase rules present); a real generation + UI click-through still pending on Max's machine. Prior session: reel note-rotation (`exclude_used_in`), v2.6 committed as `0a08923` on `ideas-tab` (119 files), `data/` gitignored.
- **Pending ops:** (1) run `migrate_backfill_processed.py` once locally; (2) first nightly routine run — click "Run now" in Cowork Scheduled sidebar to pre-approve tools; (3) `ideas-tab` branch NOT yet pushed/merged to `main` (v2.7 changes uncommitted). Rotation guards reels only — LinkedIn/`content_drafts` has none; "used" counts killed drafts (rejected notes won't return).
- **Constraints:** Sandbox blocks OpenRouter (SOCKS) → all generation must run on Max's machine. Preview tab runs offscreen → framer-motion entrance anims freeze at `opacity:0` (cosmetic; data loads fine) — do final visual checks in a focused browser.
- **Findings/notes (retained):** Voice GENERALIZES across themes; dominant quality driver is **source concreteness, not framework** (rich→clean, thin→fabricated). Defaults: ref2-bold + ref1-contrarian; weakest: ref1-bold_claim, ref6-bold. Framework UI titles are misleading filenames (ref2-bold=`90-Day Python Roadmap`, ref1-contrarian=`reel_source`, ref3-pain=`Visibility Fear`, ref1-bold=`Storytelling Insight`, ref6-bold=`3 Creator Mistakes`). `script_writer.py --story-id` int-typed → use `gen_one_node.py`. Reel routing: `/reels/generate` → `router.chat(override_model=...)`, no fallback (failing model = 500, not masked).
