# Blueprint v2.6 — Content Lifecycle (Studio queue · Asana sync · verdict loop)

## State
v2.5 monorepo. FastAPI :9000 (`NOTION DIARY FETCHER/api/main.py`), SQLite `NOTION DIARY FETCHER/data/notion_diary.db`, React/Vite frontend :5173. Two content tables: `reel_scripts` (reels) and `content_drafts` (LinkedIn). Generation works end-to-end; **nothing tracks what happens to a draft after generation** — no status, no verdicts, no publishing calendar.

User decisions (2026-06-12):
1. Nightly generation = **Cowork scheduled routine** (runs locally — sandbox blocks OpenRouter; DB is local). Morning digest is prepared inside the routine but **gated until ≥30 posts are approved in advance**.
2. Lifecycle calendar lives in **Asana** → project "Content calendar" (workspace MaxVibe `1213168548538118`, project `1214297039839658`), sections: Reference `1214297039839660`, Content in progress `1214297039839678`, Content ideas `1214297039839679`. Default view: calendar.
3. Teleprompter: skipped.
4. Caption + CTA generated **only after** a draft is reviewed (status ≥ approved). Endpoint must reject on `queued`.
5. UI: new **Studio** tab (pipeline/queue) becomes the default home tab.
6. Verdict loop: 👍/👎 + note per item, stored in DB, recent notes injected into generation prompts.

### Affected files
- `frameworks/instagram_frameworks/script_writer.py` (init_db ALTERs)
- `content_writer/db.py` (run_migration ALTERs)
- `shared/shared/lifecycle.py` **(new)** — statuses, meta update, feedback block
- `NOTION DIARY FETCHER/api/reel_routes.py` — meta/package endpoints, list fields, feedback injection
- `content_writer/api_routes.py`, `content_writer/service.py` — same for LinkedIn
- `frontend/src/components/StudioTab.jsx` **(new)**, `App.jsx`, `layout/Sidebar.jsx`, `layout/MobileNav.jsx`, `reelApi.js`, `contentWriterApi.js`
- Cowork scheduled task (created via scheduled-tasks MCP, not in repo) + `handoff/routine_nightly_content.md` (routine prompt mirror, in repo)

## Logic

### Lifecycle
`queued → approved → recorded (reels only) → posted` · terminal alternative: `killed`.
New columns on **both** `reel_scripts` and `content_drafts`:
`status TEXT DEFAULT 'queued'`, `verdict INTEGER` (1/-1/NULL), `verdict_note TEXT`, `caption TEXT`, `cta TEXT`, `asana_task_gid TEXT`, `posted_at TEXT`.

### Endpoints (mirrored on both routers)
- `PATCH /reels/scripts/{id}/meta` · `PATCH /content-writer/drafts/{id}/meta`
  body: any of `{status, verdict, verdict_note, asana_task_gid}`. Validates status ∈ set; sets `posted_at` when status→posted. Returns full row.
- `POST /reels/scripts/{id}/package` · `POST /content-writer/drafts/{id}/package`
  409 if status == queued/killed (review gate). Builds caption+CTA prompt from current `generated_text`, calls `openrouter.router.chat` (task `generate_reel_script` / `generate_linkedin_post`, optional `model` override in body), parses `CAPTION:` / `CTA:` markers, saves columns, returns them.
- List endpoints now return the new columns; optional `?status=` filter.

### Feedback injection (#6)
`shared.lifecycle.get_feedback_block(conn, table, limit=6)` → recent non-empty `verdict_note` rows (👍 prefixed KEEP / 👎 prefixed AVOID) as a `RECENT EDITORIAL FEEDBACK` block appended to the generation prompt in: reel `generate` + `generate/stream`, content-writer `prepare_prompt` (covers non-stream + stream).

### Studio tab (#5)
Default tab. Three groups: **QUEUE** (queued), **IN PRODUCTION** (approved/recorded), **SHIPPED** (posted, latest 10). Each card: channel badge, framework, model, date, expandable text, actions by state:
queued → Approve / Kill (+ verdict 👍/👎 + note saved on blur)
approved → Generate caption+CTA / Mark recorded (reel) / Mark posted / Copy post (LinkedIn: text+caption+cta)
posted → read-only.
Header: backlog meter `approved-ahead / 30` + posted-last-30-days count.
Sidebar/MobileNav: Studio first; default `tab = "studio"`.

### Cowork routine (#1 + Asana #2)
Daily 06:30, cwd = repo root. Steps:
1. Top-up: if `COUNT(queued) < 6` across both tables → `uv run batch_generate.py --stories 2 --frameworks 2` (defaults ref2-bold + ref1-contrarian per strategy log).
2. Asana sync (MCP): items with status approved/recorded and `asana_task_gid IS NULL` → create task in "Content in progress" (`due_on` = next free day with no existing content task), write gid back via meta PATCH (or sqlite3 if API down). status=posted & gid → complete task. killed & gid → complete with note "[killed]".
3. Digest gate: if approved-ahead ≥ 30 → write morning digest (top queued candidates + today's scheduled post); else print one-line status only. **Do not send digest before the 30-post backlog exists.**

## Specs
Python 3.12 / uv; sqlite ALTERs idempotent (try/except like existing pattern); business logic in `shared.lifecycle`, not in route bodies beyond glue; React: logic in api modules, StudioTab presentational+local state; Tailwind idioms match existing components (glass-panel, font-label-caps).

## Definition of Done
- Both tables carry lifecycle columns after server start (auto-migration).
- `PATCH …/meta` transitions status & stores verdicts; `POST …/package` 409s on queued, returns caption/cta on approved.
- Generation prompts include feedback block when verdict notes exist.
- Studio tab renders pipeline from live API, is the default tab, actions round-trip.
- Cowork scheduled task exists (daily 06:30) with the routine prompt; prompt mirrored at `handoff/routine_nightly_content.md`.
- `md/checkpoint.md` updated to v2.6.
