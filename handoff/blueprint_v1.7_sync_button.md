# Plan — Diary Staleness Fix: Catch-up + "Sync now" Button/Endpoint

## Context
- **Problem:** Diary tab shows entries only through Apr 24, 2026; today is May 13, 2026. ~19 days of Notion diary pages are missing from the UI.
- **Root cause (confirmed):** The Notion → SQLite sync is a fully manual CLI (`uv run python main.py` from `NOTION DIARY FETCHER/`). There is no cron, no launchd job, no API trigger, and no refresh button. The DB stops advancing whenever the user forgets to run it.
- **Decision (user-confirmed):**
  1. Catch up the 19 missing days *first* via a one-shot manual run (verifies the existing pipeline still works against current Notion before adding automation on top).
  2. Add a **"Sync now" button in the Diary tab** + a **POST `/sync` endpoint** that runs `run_sync` as a FastAPI background task. No daemon, user-initiated only.
- **Out of scope:** Scheduled launchd / cron job (rejected); downstream re-extraction of `story_nodes` after sync (existing `main.py` doesn't do this either — parity).

## Affected Files
| File | Change |
|------|--------|
| `NOTION DIARY FETCHER/api/main.py` | Add `POST /sync` endpoint + `GET /sync/status` for polling. Loads `.env` and `config.toml` lazily. |
| `frontend/src/api.js` | Add `triggerSync()` and `fetchSyncStatus()` wrappers. |
| `frontend/src/components/PageList.jsx` | Add "Sync now" button in header (next to "83 entries"); show spinner + result toast; auto-refetch `/pages` on success. |
| *(unchanged but used)* `NOTION DIARY FETCHER/src/notion_fetcher/sync.py` → `run_sync(token, database_id, config)` is invoked as-is. |

## Step 1 — Catch-up (manual, user runs, no code)
```
cd "NOTION DIARY FETCHER"
uv run python main.py
```
**Expected:** logs report ~19 new pages fetched; DB count rises from 83 → ~102; latest `created_time` ≥ 2026-05-12. Refresh the Diary tab and visually confirm May entries appear.

If this step fails (auth, schema drift, rate limit), stop — fix the pipeline before adding the UI button. The button just wraps the same call, so it will fail the same way.

## Step 2 — Backend: `/sync` endpoint (Blueprint for Gemma4)

`NOTION DIARY FETCHER/api/main.py` — additions only

```
Module: api.main (additions)
  Imports: os, threading, from dotenv import load_dotenv, from pathlib import Path,
           from notion_fetcher.sync import run_sync, from fastapi import BackgroundTasks
  Module-level state:
    _sync_state: dict = {"status": "idle", "started_at": None, "finished_at": None,
                         "error": None, "added": None}
    _sync_lock: threading.Lock
  Functions:
    _run_sync_job() -> None
      Key rules:
        - Acquire _sync_lock non-blocking; if already held, set status="busy" and return.
        - Load .env from repo root (parent of "NOTION DIARY FETCHER"); read NOTION_TOKEN, NOTION_DATABASE_ID.
        - Load config.toml from "NOTION DIARY FETCHER/config.toml".
        - Snapshot pre-count of pages table; call run_sync(...); snapshot post-count.
        - Update _sync_state: status="ok"|"error", added=post-pre, error=str(exc) on failure.
        - Always release the lock and stamp finished_at (UTC ISO).
      Calls: notion_fetcher.sync.run_sync, sqlite3 for pre/post count.
    POST /sync(background_tasks: BackgroundTasks) -> dict
      Key rules:
        - If _sync_state["status"] == "running": return 409 {detail: "sync already running"}.
        - Set _sync_state = {"status": "running", "started_at": now_iso(), ...}
        - background_tasks.add_task(_run_sync_job)
        - Return {"status": "running", "started_at": ...}.
    GET /sync/status() -> dict
      Returns a copy of _sync_state.
  Notes:
    - DO NOT call logging.basicConfig in _run_sync_job (already done inside run_sync; CLAUDE.md §7).
    - .env path: Path(__file__).parent.parent / ".env"  (NOTION DIARY FETCHER/.env)
    - Keep run_sync's own logging untouched.
```

## Step 3 — Frontend: button + polling

`frontend/src/api.js` — additions
```
export async function triggerSync() -> Promise<{status, started_at}>
  POST `${BASE}/sync`; throw on non-2xx (treat 409 specially: return {status:"busy"}).
export async function fetchSyncStatus() -> Promise<{status, started_at, finished_at, error, added}>
  GET `${BASE}/sync/status`.
```

`frontend/src/components/PageList.jsx` — UI change
```
State additions: syncing: bool, syncMsg: string|null
Header row (line 41-44): add a right-aligned Sync button before "X entries":
  <button onClick={onSyncClick} disabled={syncing}>
    <Icon name="refresh" className={syncing ? "animate-spin" : ""}/> Sync
  </button>
Behavior:
  - onSyncClick: call triggerSync(); set syncing=true.
  - Poll fetchSyncStatus() every 2s until status in {"ok","error","idle"}.
  - On "ok": refetch fetchPages(), setPages(...), setSyncMsg(`+${added} new`).
  - On "error": setSyncMsg(`Sync failed: ${error}`); keep current list.
  - Clear syncMsg after 5s; clear syncing flag when polling resolves.
Reuse existing GlassPanel/Icon style tokens; no new design tokens.
```

## Definition of Done
- [ ] `sqlite3 data/notion_diary.db "SELECT MAX(created_time) FROM pages"` returns a 2026-05-1x date.
- [ ] `curl -X POST http://localhost:8000/sync` returns `{"status":"running",...}`.
- [ ] `curl http://localhost:8000/sync/status` eventually shows `"status":"ok"` with `"added": <int>`.
- [ ] A second `POST /sync` during a run returns HTTP 409.
- [ ] Diary tab shows a Sync button; clicking it spins, then list updates with new entries and a "+N new" toast.
- [ ] Errors (e.g. missing `NOTION_TOKEN`) surface in `/sync/status.error` and as a visible toast in the UI.
- [ ] No `logging.basicConfig` introduced outside `run_sync`. No new dependencies. No changes to story_nodes / narrative / reel routers.

## ⚠️ User Verification Report
Before moving on, please report each:
1. Step 1 catch-up: did `uv run python main.py` complete cleanly? Page count before/after?
2. After Step 2: does `curl -X POST :8000/sync` succeed and does `/sync/status` flip to `ok`?
3. After Step 3: does the Sync button in the Diary tab work end-to-end (spinner → updated list → toast)?
4. Anything failed or missing — list it here so we re-spec before the next milestone.

## Handoff
Per CLAUDE.md §6, code for Steps 2 & 3 will be written by Gemma4 e2b from this Blueprint. After approval I will copy this file to `handoff/blueprint_v1.7_sync_button.md` for handoff; Haiku validates the output against the Definition of Done.
