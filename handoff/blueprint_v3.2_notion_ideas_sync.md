# Blueprint v3.2 — Notion Ideas Sync (§3) + Reel-Scan Tuple Bugfix

_2026-07-04 · Planning: Fable 5 · Execution: Sonnet 5._

## Context

PRD v3.0 §3 is the next unstarted step: pull content ideas from Max's Notion database into the `ideas` table (Notion wins for content) and push PBS lifecycle status back to Notion (PBS wins for status). This gives PBS its real inflow — ideas born in Notion, drafted in PBS, status visible back in Notion. Bundled in: the open QA bug where every reel reference scan crashes (`'tuple' object has no attribute 'strip'`).

**Decisions made with Max this session:**
- Scope = §3 + tuple bugfix. §4 tiers stay deferred (but Pillar/Tier columns land now as groundwork).
- Target DB = the **existing "CONTENT" inline database** on the Notion "Personal branding" page (page `331bc1f737a0804a82cecdc8d2dfa24f`), **extended** with Pillar/Tier selects by Max manually.
  - Database ID: `348bc1f737a0803d94c6df4385d79866` (data source `348bc1f7-37a0-808e-b1fc-000ba8f09521`).
  - Current schema: `Name` (title), `Description` (text), `Select` (multi-select: `IG`, `Linkedin` — this is the channel), `status` (status: Not started / Script ready / In progress / Done).
- Status mapping = PBS lifecycle → Max's existing 4 options **+ one new manual "Killed" option** (Notion API cannot create status options — manual step required).
- Local ideas (created in the Ideas tab, no Notion row) stay local — never pushed up to Notion.

## Max's manual pre-work (before or during execution — sync degrades gracefully without it)

1. In the CONTENT DB: add status option **`Killed`** (under Complete group).
2. Add select property **`Pillar`** with options: `it-ai-career`, `runner`, `systems-for-living`.
3. Add select property **`Tier`** with options: `scripted-headshot`, `beat-edit`, `raw-talking-head`.
4. Add to `NOTION DIARY FETCHER/.env`: `NOTION_IDEAS_DATABASE_ID=348bc1f737a0803d94c6df4385d79866` (NOTION_TOKEN already there; integration already has access to the Personal branding page — child DBs inherit).
5. (Unrelated reminder from checkpoint: rotate the leaked OpenRouter key on OpenRouter's side.)

## Part A — Bugfix: reel scan tuple crash

`frameworks/instagram_frameworks/extract_reel.py:431` passes the whole `(content, model_used)` tuple from `llm_client.complete()` into `parse_yaml_with_fallback()`. Fix: unpack the tuple (mirror `script_writer.py:206`, which does it correctly) and keep `model_used` if the surrounding code records it. One-line change; no schema impact.

## Part B — §3 Notion ideas two-way sync

### B1. Schema: extend `ideas` table (`ideas/repository.py` → `run_migration`)

New columns via the existing try/except `ALTER TABLE` pattern:

- `notion_page_id TEXT` (unique per idea; upsert key)
- `pillar TEXT`, `tier TEXT` (nullable — populated from Notion once Max adds the properties; §4 groundwork)
- `channels TEXT` (JSON array from the `Select` multi-select, e.g. `["IG","Linkedin"]`)
- `notion_last_status TEXT` (last lifecycle status successfully pushed to Notion — change detection)
- `notion_synced_at TEXT`

Extend `Idea` pydantic model (`ideas/models.py`) and the SELECTs in `list_ideas`/`get_idea` with `notion_page_id`, `pillar`, `tier`, `channels`. Add repository functions: `upsert_idea_from_notion(conn, notion_page_id, title, body, pillar, tier, channels, now) -> (idea_id, created: bool)` (insert with `"idea_" + uuid4().hex[:8]` or update content fields by `notion_page_id` — **Notion wins for content**, local `title`/`body` overwritten for Notion-born ideas) and `derive_idea_status(conn, idea_id) -> str`.

**Idea-status derivation rule** (idea has no own status column; lifecycle lives on drafts):
- no linked drafts → `queued`
- drafts exist and ALL are `killed` → `killed`
- else furthest stage among non-killed drafts: `posted` > `recorded` > `approved` > else `drafted`

### B2. New module `notion_ideas/` (business logic, no UI)

Reuses `NotionClient` from `NOTION DIARY FETCHER/src/notion_fetcher/client.py` (paginated `get_all_database_pages`, 429 retry already built). Import via `sys.path.insert` of `.../NOTION DIARY FETCHER/src` — same pattern `jobs/handlers.py` already uses. `notion-client==2.2.1` + `python-dotenv` are already in `NOTION DIARY FETCHER/pyproject.toml`.

- `notion_ideas/config.py` — load `NOTION_TOKEN` + `NOTION_IDEAS_DATABASE_ID` from the `NOTION DIARY FETCHER/.env` (python-dotenv, same as existing code). Missing config → clear error string surfaced through the job's `error` field, never a crash at import time.
- `notion_ideas/mapper.py` —
  - `page_to_idea_fields(page: dict) -> dict`: Notion page object → `{title, body, pillar, tier, channels}`. Title from `Name`, body from `Description` rich-text (page-body blocks deferred), pillar/tier from selects **if the properties exist** (absent → `None`, no failure), channels from `Select` multi-select.
  - `LIFECYCLE_TO_NOTION_STATUS`: `queued→"Not started"`, `drafted→"Script ready"`, `approved→"Script ready"`, `recorded→"In progress"`, `posted→"Done"`, `killed→"Killed"`.
- `notion_ideas/sync.py` —
  - `pull_ideas(conn) -> summary dict` (`{pulled, created, updated}`): query all DB pages, upsert each by `notion_page_id`. Never deletes; ideas whose Notion page disappears simply stop updating. Notion `status` is **ignored on pull** (PBS owns status).
  - `push_status(conn, idea_id) -> summary dict`: skip if idea has no `notion_page_id`; derive status, map it; if `!= notion_last_status`, `client.pages.update(page_id, properties={"status": {"status": {"name": mapped}}})`, then record `notion_last_status` + `notion_synced_at`. If the mapped option doesn't exist in Notion (e.g. `Killed` not yet added), surface the API error in the job's `error` field — next status change retries naturally.
- `notion_ideas/routes.py` — `POST /notion/sync` → `jobs_queue.enqueue("sync_notion_ideas", {})` → `{"job_id": ...}`. Mount in `NOTION DIARY FETCHER/api/main.py` alongside the other routers.

### B3. Job kinds (`jobs/handlers.py` + `register()`)

- `sync_notion_ideas` → `notion_ideas.sync.pull_ideas`
- `push_notion_status` (payload `{idea_id}`) → `notion_ideas.sync.push_status`

**Push triggers** (fire-and-forget enqueue, never blocks the caller):
1. Studio status changes — after successful `update_meta` in `content_writer/api_routes.py:119` (`patch_draft_meta`) and `NOTION DIARY FETCHER/api/reel_routes.py:147` (`patch_script_meta`): if the row has an `idea_id`, enqueue `push_notion_status`.
2. Draft generation — at the end of `_handle_generate_linkedin` / `_handle_generate_reel` in `jobs/handlers.py`, after `link_draft`/`link_reel` when `idea_id` is set: enqueue `push_notion_status` (idea becomes `drafted` → "Script ready"). Enqueueing from inside a handler is safe — single worker just processes it next.

### B4. Frontend (display + one button; logic stays server-side)

- `lib/ideasApi.js`: add `syncNotionIdeas()` → `POST /notion/sync`.
- `IdeasTab.jsx`: "Sync from Notion" button → enqueue, poll with the existing `lib/useJob.js` hook, refresh the ideas list `onDone`, show summary/error inline. Show pillar/tier/channel badges on idea rows when present.
- `IdeaDetail.jsx`: show pillar/tier/channels + a small "Notion-linked" indicator. **Read-only** — content edits for Notion-born ideas belong in Notion (conflict rule); no pillar/tier editors for local ideas until §4 needs them.

## Post-implementation fix (same session, after Max's manual QA)

Max's manual test on the real CONTENT database showed most idea content lives in the **page body** (blocks), not the `Description` property — `Description` was empty on ideas like "Iteration" and "Redoing TurboBaba" whose real content was written directly under the page. `pull_ideas` now falls back to `client.get_page_blocks(page_id)` (already in `NotionClient`, reused) → `mapper.blocks_to_text()` whenever `Description` is empty, flattening `paragraph`/`heading_*`/list/`quote`/`callout`/`toggle`/`to_do` blocks to plain text in order. This replaces the original "Description property only, v1" scope note below.

Also confirmed live: the Notion integration token has real write access (a transient 403 during initial testing turned out to be a one-off, not a permissions gap — a direct round-trip status update succeeded cleanly).

## Explicitly out of scope (unchanged from PRD)

Scheduled VM pull (§7 — manual Sync button only for now) · tier-specific prompts (§4 — tier is stored, not yet used) · draft versioning (§5) · pushing local ideas up to Notion · Notion-side deletion propagation · stale `yaml_path` pass.

## Definition of Done

1. ✅ Reel reference scan of a real MP4 completes without the tuple crash. Max re-ran a live extraction test after confirming it runs through the current app (not the stale `~/Documents/personal_brand` copy) — passed.
2. ✅ `POST /notion/sync` pulls the CONTENT DB rows into the Ideas tab (title, body, channels; pillar/tier once Max adds the properties). Re-running sync after editing a row in Notion updates the PBS idea (Notion wins for content). *Verified live against the real database — see below.*
3. ✅ Generating a draft for a Notion-born idea flips its Notion status to "Script ready"; approving/recording/posting/killing in Studio moves it to the mapped option — visible in Notion without touching it. *Verified via the job queue and a direct round-trip status update, and confirmed by Max click-testing the full Ideas → Studio → Notion path in the browser.*
4. ✅ Local ideas (no `notion_page_id`) keep working exactly as before, untouched by sync. Confirmed by Max during the manual QA pass.
5. ✅ `python -c "import api.main"` clean (new router + migrations registered) · `npm run build` (Vite) clean. Missing-`.env`-config error path (`ConfigError`) exists but was not explicitly exercised — low risk, not blocking.

Max ran the full QA checklist from this session (Ideas tab click-through, Notion-linked read-only fields, draft generation → status push, Studio approve/kill/record/post → Notion status, local-idea isolation) and confirmed everything passes.

## Verification performed this session

1. Backend: ran the startup event directly; confirmed all 6 new `ideas` columns exist in `notion_diary.db`.
2. Live pull: ran `pull_ideas()` against the real CONTENT database — 16 real ideas pulled and upserted. Re-ran immediately after — idempotent (0 created, 16 updated, no duplicates).
3. Live push: ran `push_status()` through the actual job queue (enqueue → worker → `done`) against a real Notion page; separately round-tripped a direct status write (`In progress` → `Not started`) to positively confirm write access (the first attempt had thrown a transient 403, which this round-trip showed was not a real permissions gap).
4. Body-content gap found + fixed: Max noticed "Iteration" and "Redoing TurboBaba" synced with empty bodies. Root cause: their content lives in the Notion page body (blocks), not the `Description` property, which was the v1 pull source. Fixed same-session (see "Post-implementation fix" above) and re-verified — all 16 ideas now carry real body text (32–4422 chars).
5. `npm run build` — clean, both before and after the body-content fix.
6. `python -c "import api.main"` — clean, re-checked after the body-content fix.

## Still open (not blocking, Max's own follow-up)

- Add the `Killed` status option + `Pillar`/`Tier` select properties in Notion (still pending from "Max's manual pre-work" above) — pillar/tier currently `None` on all 16 synced ideas.

## Post-QA fix: reject-without-reason (StudioTab.jsx)

Found during Max's manual QA pass: `PipelineCard.confirmReject` in `frontend/src/components/StudioTab.jsx` hard-blocked the "Reject" action unless a reason was typed (`if (!reason.trim()) { setErr(...); return }`). The backend never required this — `verdict_note` is optional in `update_meta`/`META_COLUMNS` (`shared/shared/lifecycle.py`). This was a frontend-only restriction, not a spec requirement.

Fix: removed the blocking validation; `confirmReject` now sends `verdict_note` only when non-empty (so a blank reject doesn't add a hollow entry to the "avoid this" feedback block read by `get_feedback_block`). Placeholder text updated to read "(optional — feeds the next batch as 'avoid this')". Rejecting with an empty reason field now works via both the Confirm button and Enter. `npm run build` re-verified clean after the change.

## Handoff note (model routing)

Execution → Sonnet 5 per CLAUDE.md routing. Sequence: Part A bugfix → B1 migration → B2 module → B3 jobs/triggers → B4 frontend → verification → body-content fix → reject-without-reason fix. Nothing here needed sub-agents.
