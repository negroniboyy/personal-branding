# Blueprint v3.1 — QA Fixes: Jobs Queue, LLM Framework Picker, Cleanup

_2026-07-03 · Planning model: Fable 5 · Execution model: Sonnet 5 · Status: implemented, awaiting Max's manual QA re-pass before commit._

## Why (the problem)

Max ran the manual QA checklist on the v3 §2 idea-only reboot and found real breakage and friction, not just polish items: the reels reference-scan was hard-failing on a dead OpenRouter model slug, long-running work (draft generation, MP4 folder scan) had no resilience if the browser tab closed or the server restarted mid-run, and the framework `<select>` dropdowns + domain chips were leftover decision-fatigue UI from the retired story-node path. This blueprint fixes all of that and adds the groundwork (per-framework outcome stats) for the future §9 auto-prune feedback loop.

## 1. STATE

**Before this session:** `personal_brand` v3 §2 (idea-only reboot) merged but uncommitted. Reels scan endpoint (`POST /reels/scan`) synchronously processed all queued MP4s in one blocking request behind a `threading.Lock`; draft generation (`POST /content-writer/generate`, `POST /reels/generate`, `POST /ideas/{id}/drafts/{channel}`) ran synchronously in the request handler — closing the tab or a server restart lost the work. Framework selection for LinkedIn/Reel generation was a manual dropdown fed by a crude keyword-overlap scorer (`content_writer/recommender.py`, `frameworks/instagram_frameworks/script_writer.score_frameworks`). LinkedIn had 11 frameworks, 3 of which were exact duplicates (same source post extracted twice under different `hook_type` labels).

**What this session keeps:** Studio tab and lifecycle untouched. Ideas tab is still the primary generation surface; Writer/Reels tabs still exist as one-off generation surfaces (not folded into Ideas). Notion sync (§3), tier prompts (§4), draft versioning (§5), VM deploy (§7), and the in-app insight helper (§8) are all still deferred, unchanged from the v3.0 PRD.

**Affected files:** see §2–§5 below.

## 2. NEW MODULE — `jobs/` (background job queue)

A deep module hiding persistence + threading behind four functions:

- `jobs/queue.py` — `enqueue(kind, payload) -> job_id`, `get_job(job_id)`, `list_jobs(status?, kind?, limit)`, `register(kind, handler)`. Implementation: a `jobs` table in the existing `notion_diary.db` (`id, kind, payload_json, status queued|running|done|failed, result_json, error, created_at, started_at, finished_at`), one daemon worker thread (`start_worker()`, idempotent) draining an in-memory `queue.Queue` backed by the SQLite table as source of truth. `recover_stale_jobs()` marks any `running` row `failed` on startup (crash/restart recovery) — verified live by killing a job mid-`running` and confirming recovery.
- `jobs/routes.py` — `GET /jobs/{id}`, `GET /jobs?status=&kind=`.
- `jobs/handlers.py` — thin wrappers registered against `jobs/queue.py`, imported automatically via `jobs/__init__.py` so any `from jobs import queue` elsewhere makes handlers available without a separate import. Three job kinds:
  - `generate_linkedin_draft` / `generate_reel_script` — shared by both the idea-linked flow (Ideas tab, `idea_id` set) and the one-off flow (Writer/Reels tabs, `idea_id: null`). Calls `frameworks.picker.pick_framework` when no `framework_id` is supplied.
  - `scan_reference_file` — one job per `.mp4`; a failed job's `error` field *is* the per-file failure reason (replaces the old `succeeded[]/failed[]` response arrays).
- Wired into `NOTION DIARY FETCHER/api/main.py`'s startup event: `run_migration()` → `recover_stale_jobs()` → `start_worker()`, and `jobs.routes.router` mounted alongside the other routers.
- Converted endpoints now return `{"job_id": ...}` immediately: `POST /ideas/{id}/drafts/linkedin`, `POST /ideas/{id}/drafts/reel`, `POST /reels/generate`, `POST /content-writer/generate`, `POST /reels/scan` (now enqueues one job per file and returns `{"queued": N, "jobs": [{"file", "job_id"}], "references_dir"}`). The old `_scan_lock` is gone — serialization is now free, since the worker thread processes one job at a time.
- **Removed as dead code** (found unreachable from the frontend, would have needed parallel maintenance against the new job flow): `POST /content-writer/generate/stream` and `POST /reels/generate/stream` (SSE streaming generation — never called by any frontend code).
- Frontend: `frontend/src/lib/useJob.js` — a `useJob(jobId, {onDone, onError})` polling hook (2s interval). `IdeaDetail.jsx`, `ContentWriter.jsx`, `ReelWriter.jsx` all use it for generation; `ReelWriter.jsx`'s scan panel renders one `<ScanJobRow>` per enqueued file, each independently polling its own job. Leaving the page and coming back loses nothing.

## 3. NEW MODULE — `frameworks/picker.py` (LLM framework picker)

`pick_framework(conn, channel, idea_prompt) -> (framework_id, reason)`. Builds a compact prompt listing every framework's `id/hook_type/tone/cta/topics/description`, asks a cheap model (`pick_framework` task, new entry in `config/openrouter_models.yaml`: primary `openai/gpt-oss-120b:free`, secondary `google/gemma-4-26b-a4b-it` — reuses already-vetted models) for strict JSON `{"framework_id", "reason"}`, validates the id exists, and **falls back to the existing keyword scorer on any failure** (bad JSON, unknown id, LLM error) so generation never blocks on the picker.

- `framework_pick_reason` column added to `content_drafts` and `reel_scripts` (migrations in `content_writer/db.py` and `frameworks/instagram_frameworks/script_writer.py`); threaded through `ContentDraft`/`GenerateResult` dataclasses, `ideas.models.IdeaDraft`, and every list/get endpoint so the UI can show "Framework: X — reason" on generated drafts.
- UI removal: framework `<select>` dropdowns in `IdeaDetail.jsx`, `ContentWriter.jsx`, `ReelWriter.jsx`; `DomainChips` usage; "Get Recommendations" buttons. Deleted now-dead files: `components/DomainChips.jsx`, `lib/domains.js`, `lib/frameworkLabel.js`. `/recommendations` endpoints and the keyword scorer stay (they're the picker's fallback path) but the frontend no longer calls them directly.
- **Decision (confirmed with Max):** no hard cap on framework count. An LLM picker doesn't suffer from the decision-fatigue problem a human dropdown did — more distinct frameworks genuinely improve match quality. Pool *quality* (no near-duplicates) matters more than pool *size*.

## 4. FRAMEWORK OUTCOME STATS + DEDUPE

- `GET /frameworks` and `GET /frameworks/{channel}/{id}` (`frameworks/api_routes.py`) now return `used`/`approved`/`killed` counts per framework via a `LEFT JOIN` subquery against `content_drafts`/`reel_scripts` grouped by `framework_id` and `status`. `FrameworksTab.jsx` shows these in both the list rows and the detail header. This is the data source a future §9 "suggest deletion" nudge would read from — not built this session, just logged.
- **LinkedIn dedupe applied** (proposed by Fable, confirmed by Max before execution): 3 of 11 LinkedIn frameworks were exact duplicates — the same source LinkedIn post extracted twice under two different `hook_type` labels (identical `raw_excerpt`/CTA link, near-identical structure):
  | Archived | Kept | Why |
  |---|---|---|
  | `2-linkedin-bold_claim-v1` | `2-linkedin-contrarian-v1` | keeper has real usage history (1 draft generated) |
  | `5-linkedin-pain_point-v1` | `5-linkedin-bold_claim-v1` | keeper has the more complete structure (4 steps vs 3) |
  | `7-linkedin-bold_claim-v1` | `7-linkedin-pain_point-v1` | keeper's structure names a more specific technique (❌/✅ rebuttal pattern) |

  Archived YAMLs moved to `_archive/frameworks_dedupe_linkedin/`; DB rows deleted. LinkedIn frameworks: 11 → 8.
- **Found, not fixed (flagging for a future session):** every framework's `yaml_path` column in `notion_diary.db` points to a stale legacy location (`/Users/maxkiyuna/Documents/personal_brand/...`) from before the repo moved under `BrandStudio/`. The Frameworks tab's read/write/delete operations all silently operate on that legacy copy, not the tracked copy under `frameworks/*/frameworks/*.yaml` in this repo — which means the repo's own YAML files are stale and edits made via the UI never land in version control. Worth a dedicated pass (recompute `yaml_path` relative to the current repo root) before this bites someone.

## 5. CONFIG FIX — dead OpenRouter model slugs

`config/openrouter_models.yaml` → `extract_reel_framework`: the reported error (`deepseek/deepseek-v4-flash:free` → 404, "paid version available, use deepseek/deepseek-v4-flash") was confirmed live against `GET https://openrouter.ai/api/v1/models`. The primary, `google/gemma-4-31b-it:free`, still exists but almost certainly failed silently first (free-tier rate limiting is the common failure mode) before falling through to the dead secondary. Fixed by promoting the cheap paid model to primary and demoting the free one to fallback:
```yaml
extract_reel_framework:
  primary:   deepseek/deepseek-v4-flash       # was google/gemma-4-31b-it:free
  secondary: google/gemma-4-31b-it:free       # was deepseek/deepseek-v4-flash:free (dead)
```

## 6. SPECS

Python 3.12/uv, FastAPI, SQLite (same `notion_diary.db`, no new database), React 18/Vite/Tailwind, business logic in builders not UI files (root CLAUDE.md rule), archive-don't-delete for removed framework YAMLs.

## 7. DEFINITION OF DONE

1. ✅ Reels folder scan runs against live, verified-available model slugs. *(Not re-run against a real MP4 this session — no reference file was available in the sandbox; the job plumbing itself was verified end-to-end with a synthetic handler.)*
2. ✅ Generation + scan run as background jobs; verified live: enqueue → worker picks up → `done`/`failed` status; a job stuck in `running` is marked `failed` on `recover_stale_jobs()` (simulated restart).
3. ✅ Dropdowns/chips removed from all three generation surfaces; every new draft records `framework_id` + `framework_pick_reason`.
4. ✅ Frameworks tab shows outcome stats; dedupe applied (11 → 8 LinkedIn frameworks), confirmed with Max before execution.
5. ✅ Backend boots clean (`api.main` imports + startup event both run without error); `vite build` passes. Studio tab untouched — approve/kill/caption/post flow not modified by this session.

## Verification performed this session

- `python -c "import api.main"` — full router registration succeeds, `/jobs/{id}` and `/jobs` present in route table.
- Ran the FastAPI startup event directly (migrations + `jobs` table creation + worker start) — succeeded, `jobs` table confirmed present.
- Enqueued a synthetic job against the real worker thread — reached `done` with the correct result within one poll cycle.
- Simulated a stale `running` job and called `recover_stale_jobs()` — correctly marked `failed` with `error: "interrupted by server restart"`.
- Tested the new framework-stats SQL directly against the live DB — correct counts.
- `npm run build` (Vite) — clean, no import errors, after every frontend edit round.
- Test rows (`jobs`, dedupe test artifacts) cleaned from the real dev DB before finishing.

## Still to verify (needs Max, or a live OpenRouter budget)

- A real end-to-end generation call through `pick_framework` (this session only exercised the fallback path to avoid spending API credits without explicit sign-off) — sanity-check the picker's JSON parsing against real model output.
- A real MP4 through the fixed `extract_reel_framework` chain.
- Live click-through of Ideas/Writer/Reels tabs in the browser (this session verified via `vite build` + backend import checks, not a driven browser session).

## Explicitly out of scope (unchanged from v3.0 PRD)

Notion ideas DB two-way sync (§3), tier-specific prompt templates (§4), draft versioning (§5), GCP VM deploy + scheduled automation (§7), in-app insight helper (§8, still a documented agent workflow only), automated "suggest deletion" nudge (§9 — the stats data now exists, the nudge logic doesn't yet), Writer/Reels tab consolidation into Ideas (considered, deferred — Studio stays the review board, inflow arrives with §3).
