# Ideas Feature — Design Spec
Date: 2026-05-13

## Context
The Content Writer and Reels tabs require a story node as the entry point for generation. This works for reflective content derived from diary entries, but leaves no path for capturing spontaneous insights — ideas that arrive outside of any journaling session. This spec defines an Ideas tab where the user captures raw ideas, optionally attaches a story for grounding, and generates LinkedIn drafts or Reel scripts inline without leaving the tab.

---

## Section 1 — Architecture & Data Model

### New table: `ideas`
```sql
CREATE TABLE IF NOT EXISTS ideas (
  id TEXT PRIMARY KEY,          -- e.g. "idea_a1b2c3d4"
  title TEXT NOT NULL DEFAULT '',
  body  TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,     -- ISO-8601
  updated_at TEXT NOT NULL
);
```

### Migrations to existing tables (nullable additions, safe to re-run)
```sql
ALTER TABLE content_drafts ADD COLUMN IF NOT EXISTS idea_id TEXT REFERENCES ideas(id);
ALTER TABLE reel_scripts   ADD COLUMN IF NOT EXISTS idea_id TEXT REFERENCES ideas(id);
```
`story_node_id` on both tables stays as-is but becomes functionally optional when `idea_id` is set — no column change needed; the service layer accepts `null`.

### Principle
Existing Writer and Reels tabs are untouched. Ideas is an additive feature; it reuses existing generation services rather than forking them.

---

## Section 2 — Ideas Tab: UI Layout (Master-Detail)

### Left rail (≈38% width, scrollable)
- Search/filter input at top
- `+ New Idea` button (same target as the sidebar CTA)
- Idea list, sorted by `updated_at` desc — each row shows title, draft count badge, recency chip
- Active idea highlighted with primary gradient pill
- Empty state: dashed card "Capture your first idea"

### Right pane (≈62% width)
**Idea editor (top)**
- Title: large single-line field, editable inline
- Body: 4–6 row monospace textarea, same style as Idea Hint in Writer tab
- Auto-save on blur — no explicit save button

**Generation controls (middle, shown once an idea exists)**
- Optional story picker — dropdown defaulting to "No story — idea only"
- Optional framework picker — auto-populates when a story is selected; shows all otherwise
- Two buttons side-by-side: `+ LinkedIn Draft` and `+ Reel Script`

**Child drafts list (bottom)**
- Section header `DRAFTS (N)`
- Each row: channel badge, framework summary, creation date, inline expand/copy
- Empty state: "No drafts yet — generate one above"

### Interactions
- Selecting an idea fades in the detail pane (no navigation)
- `+ New Idea` creates blank entry, selects it, focuses title field
- Generating a draft appends inline without leaving the tab

---

## Section 3 — Backend API

All endpoints under `/ideas`. Migration runs at startup (idempotent).

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/ideas` | List all ideas sorted by `updated_at` desc. Returns `id, title, body, draft_count, created_at, updated_at`. |
| `POST` | `/ideas` | Create blank idea. Returns full idea object. |
| `GET`  | `/ideas/{id}` | Single idea + child drafts (LinkedIn + Reel). |
| `PATCH`| `/ideas/{id}` | Update `title` and/or `body`. Auto-sets `updated_at`. |
| `POST` | `/ideas/{id}/drafts/linkedin` | Generate LinkedIn draft linked to idea. Accepts optional `story_node_id`, `framework_id`, `idea_prompt` (falls back to idea body). Reuses `ContentWriterService.generate()`. |
| `POST` | `/ideas/{id}/drafts/reel` | Same but for reel scripts. Reuses `ReelService.generate()`. |

**Request body — generate endpoints (both):**
```json
{
  "story_node_id": "sn_abc123",   // optional
  "framework_id": "fw_xyz",       // optional
  "idea_prompt": "override text"  // optional; defaults to idea.body
}
```

---

## Section 4 — Sidebar & Navigation

**`frontend/src/components/layout/Sidebar.jsx`**

1. Add 5th nav item after Reels:
   ```js
   { id: "ideas", label: "Ideas", icon: "lightbulb" }
   ```

2. Rename sidebar top button `New Draft` → `New Idea`. On click: call `onTabChange("ideas")` and emit a `create-idea` event that the Ideas tab listens for to auto-create + select a blank entry.

No mobile nav changes required.

---

## Section 5 — Affected Files

| File | Change |
|------|--------|
| `NOTION DIARY FETCHER/api/main.py` | Register `/ideas` router |
| `NOTION DIARY FETCHER/api/ideas_router.py` | New file — 6 endpoints + startup migration |
| `NOTION DIARY FETCHER/ideas/repository.py` | New file — DB queries for ideas table |
| `NOTION DIARY FETCHER/ideas/models.py` | New file — `Idea`, `IdeaDraft` Pydantic models |
| `NOTION DIARY FETCHER/ideas/service.py` | New file — orchestrates create/update/generate, delegates to existing ContentWriter/Reel services |
| `frontend/src/components/IdeasTab.jsx` | New file — master-detail layout |
| `frontend/src/components/IdeaDetail.jsx` | New file — detail pane with editor + generation controls + draft list |
| `frontend/src/ideasApi.js` | New file — fetch wrappers for all 6 endpoints |
| `frontend/src/components/layout/Sidebar.jsx` | Add Ideas nav item, rename New Draft button |
| `frontend/src/App.jsx` | Add `ideas` tab case, wire `create-idea` event |

---

## Section 6 — Definition of Done

- [ ] `GET /ideas` returns empty list on fresh DB (no crash)
- [ ] Creating an idea via `POST /ideas` and patching title/body persists correctly
- [ ] `POST /ideas/{id}/drafts/linkedin` with no story returns a generated draft linked to the idea
- [ ] `POST /ideas/{id}/drafts/linkedin` with a story returns a generated draft using that story
- [ ] `GET /ideas/{id}` returns the idea with its child drafts
- [ ] Ideas tab renders master-detail; selecting an idea loads detail pane
- [ ] `+ New Idea` in sidebar navigates to Ideas tab and creates a blank entry
- [ ] `+ LinkedIn Draft` and `+ Reel Script` buttons append drafts inline
- [ ] Existing Writer and Reels tabs are unaffected
- [ ] DB migration is idempotent (safe to restart server)

---

## Section 7 — Verification Steps

1. `cd "NOTION DIARY FETCHER" && uv run uvicorn api.main:app --reload`
2. `curl -X POST http://localhost:8000/ideas` → returns idea with generated `id`
3. `curl -X PATCH http://localhost:8000/ideas/{id} -d '{"title":"Test","body":"A thought"}'`
4. `curl -X POST http://localhost:8000/ideas/{id}/drafts/linkedin` → returns `generated_text`
5. `curl http://localhost:8000/ideas/{id}` → shows idea + 1 child draft
6. Open `http://localhost:5173` → Ideas tab appears in sidebar
7. Click "New Idea" in sidebar → navigates to Ideas tab, blank entry selected
8. Type title + body, click `+ LinkedIn Draft` → draft appears in child list
