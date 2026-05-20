# PRD — Personal Branding Platform
## Part 3: Frontend, API Clients, Logging & Operations

---

## 7. Frontend Tab Structure

**App:** React + Vite · `localhost:5173`  
**Entry:** `frontend/src/App.jsx` → top-level tab router  
**API base:** `http://localhost:8000`

---

### Tab 1 — Diary

**Components:** `PageList.jsx` → `PageDetail.jsx`

**PageList:**
- Calls `GET /pages` on mount
- Renders: scrollable list, each card shows title + created date
- Click → navigate to PageDetail

**PageDetail:**
- Calls `GET /pages/{page_id}`
- Renders: page title, creation date, all blocks with type badges (paragraph, heading_1, etc.)
- Back button → return to list

**Outputs:** Read-only view of raw diary content

---

### Tab 2 — Narrative Warehouse

**Components:** `NarrativeDashboard.jsx` · `StoryNodeList.jsx` · `StoryNodeCard.jsx`

#### NarrativeDashboard

**Stat cards** (loaded on mount):
- Story Nodes: `GET /narrative/story-nodes?limit=1` → `total`
- Active Threads: `GET /narrative/threads?status=Open`
- Weeks Synthesized: `GET /narrative/weekly-index`

**Sync All section:**
- Button "Sync All" → sequential: `POST /narrative/extract` then `POST /narrative/synthesize`
- Shows last sync timestamp (localStorage)
- Result display: pages processed, nodes created, thread count, open loops, sentiment delta

**Synthesize Specific Week:**
- Dropdown of weeks from `GET /narrative/weekly-index`
- Button "Synthesize" → `POST /narrative/synthesize` with selected `week_start`
- Result: inline stats block

#### StoryNodeList

**Filters (all client-side after initial load):**
- Min Score slider (0.0–1.0)
- Flag buttons: All | Normal | Low Potential
- Text search: scans user_state, conflict_node, desired_outcome
- Sort: Score ↓ or Date ↓

**Pagination:** 20 nodes per page  
**Data:** `fetchAllStoryNodes(minScore)` — paginates `GET /narrative/story-nodes` until exhausted

#### StoryNodeCard

**Read mode:** Shows narrative_flag badge, created_time, user_state, conflict_node, desired_outcome, the_bridge, worth_score (numeric), thematic_tags chips

**Edit mode** (click Edit):
- All fields become text inputs / textarea
- Worth score: range slider
- Tags: comma-separated text input
- Save → `PUT /narrative/story-nodes/{id}` → optimistic update
- Cancel → revert

---

### Tab 3 — Content Writer (LinkedIn)

**Component:** `ContentWriter.jsx` (split panel)

#### Left Panel — Controls

1. **Idea textarea** — optional framing hint (e.g. "pivot to freelancing")
2. **"Get Recommendations" button** → `POST /content-writer/recommendations`
   - Populates story dropdown (sorted by score, shows: conflict_node + worth_score)
   - Populates framework dropdown (shows: hook_type + tone)
   - Auto-selects first of each
3. **Story picker dropdown** — manual override after recommendations
4. **Framework picker dropdown** — manual override
5. **"Generate Draft" button** → `POST /content-writer/generate`
6. **Recent Drafts list** — `GET /content-writer/drafts` on load; click item → load into right panel

#### Right Panel — Output

- Draft chips: ID · Model · Story ID · Framework ID
- `<pre>` block: `generated_text` (monospace, preserves whitespace)
- "Copy" button → clipboard

**Data Flow:**
```
Idea input
    → Recommendations (stories ranked by score + tag overlap with idea)
    → User selects story + framework
    → Generate (LLM writes post using story narrative + framework structure)
    → Draft appears in right panel + saved to content_drafts
```

---

### Tab 4 — Reels (Instagram)

**Component:** `ReelWriter.jsx` (split panel, mirrors ContentWriter)

#### Left Panel — Controls

1. **Idea textarea** — optional framing hint
2. **"Get Recommendations" button** → `POST /reels/recommendations`
3. **Story picker dropdown** — shows conflict_node + worth_score
4. **Framework picker dropdown** — shows id + hook_type + pacing + cta_type + duration_sec
5. **"Generate Reel Script" button** → `POST /reels/generate`
6. **Recent Scripts list** — `GET /reels/scripts`; click → load into right panel

**MP4 Ingest Section:**
- "Open references folder" button → `POST /reels/open-references` (opens OS file manager)
- "Scan references folder" button → `POST /reels/scan`
  - Progress: loading state while scanning
  - Result block: processed count, succeeded list, failed list with error messages
- Instruction text: explains dropping .mp4 files

#### Right Panel — Output

- Script chips: ID · Model · Story ID · Framework ID
- `<pre>` block: `generated_text`
- "Copy" button → clipboard
- Loading state: "Generating your reel script..."

**Data Flow:**
```
User drops .mp4 into references folder
    → Scan (Whisper + PySceneDetect + LLM per video)
    → New reel_frameworks available in dropdown
    → User selects story + framework
    → Generate (LLM writes scene-by-scene script)
    → Script in right panel + saved to reel_scripts
```

---

## 8. Frontend API Client Modules

**`frontend/src/api/api.js`** — Diary
- `fetchPages()` → GET `/pages`
- `fetchPage(id)` → GET `/pages/{id}`

**`frontend/src/api/narrativeApi.js`** — Narrative Warehouse
- `triggerExtract(provider, model)` → POST `/narrative/extract`
- `triggerSynthesize(weekStart)` → POST `/narrative/synthesize`
- `fetchStoryNodes({since, until, minScore, narrativeFlag, limit, offset})` → GET `/narrative/story-nodes`
- `fetchAllStoryNodes(minScore)` → paginates until total exhausted
- `updateStoryNode(id, fields)` → PUT `/narrative/story-nodes/{id}`
- `fetchWeeklyIndex(limit)` → GET `/narrative/weekly-index`
- `fetchThreads(status, limit)` → GET `/narrative/threads`

**`frontend/src/api/contentWriterApi.js`** — LinkedIn
- `fetchFrameworks()` → GET `/content-writer/frameworks`
- `postRecommendations({idea_prompt, top_n})` → POST `/content-writer/recommendations`
- `postGenerate({story_node_id, framework_id, idea_prompt, provider, model})` → POST `/content-writer/generate`
- `fetchDrafts()` → GET `/content-writer/drafts`
- `fetchDraft(id)` → GET `/content-writer/drafts/{id}`

**`frontend/src/api/reelApi.js`** — Instagram Reels
- `postReelRecommendations({idea_prompt, top_n})` → POST `/reels/recommendations`
- `postReelGenerate({story_node_id, framework_id, idea_prompt})` → POST `/reels/generate`
- `fetchReelScripts()` → GET `/reels/scripts`
- `fetchReelScript(id)` → GET `/reels/scripts/{id}`
- `postReelScan()` → POST `/reels/scan`
- `postReelOpenReferences()` → POST `/reels/open-references`

---

## 9. Logging

**Package:** `shared/shared/logger.py` (uv editable dep installed into NOTION DIARY FETCHER venv)  
**Usage:** `from shared.logger import get_logger` — one call at module top, never inside functions

**Active subsystems:**
- `narrative_warehouse` → `logs/narrative_warehouse.log`
- `instagram_frameworks` → `logs/instagram_frameworks.log`
- `linkedin_frameworks` → `logs/linkedin_frameworks.log`
- `content_writer` → `logs/content_writer.log`

**Behavior:**
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Output: timed rotating file (daily) + stderr
- Retention: 7 days (configurable via `config.toml [logger].retention_days`)
- **Never** `logging.basicConfig()` — conflicts with factory
- **Never** `print(..., file=sys.stderr)` for errors — use `logger.error()`
- `print()` is acceptable for CLI terminal UX (progress, dry-run output)

---

## 10. Run Commands

```bash
# Backend
cd "NOTION DIARY FETCHER" && uv run uvicorn api.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm run dev   # → http://localhost:5173

# Sync diary from Notion
cd "NOTION DIARY FETCHER" && uv run sync

# Extract reel framework from single .mp4
cd "NOTION DIARY FETCHER" && uv run python ../frameworks/instagram_frameworks/extract_reel.py \
  --file ../frameworks/instagram_frameworks/references/<file>.mp4

# Generate reel script (CLI)
cd "NOTION DIARY FETCHER" && uv run python ../frameworks/instagram_frameworks/script_writer.py \
  [--idea TEXT] [--story-id ID] [--framework-id ID] [--dry-run]

# After adding deps to shared/
cd "NOTION DIARY FETCHER" && uv sync
```

---

## 11. Error Handling

| Scenario | Behavior |
|----------|----------|
| Notion API error | Logged per page; sync continues to next page |
| LLM output malformed | YAML fallback parser; failed files saved to `references/failed/` |
| Empty diary page | Skipped silently; `processed_status` not updated |
| Reel extraction failure | `.mp4` moved to `failed/`; error in scan response |
| Duplicate extraction | `processed_status = 1` prevents re-extraction |
| Concurrent reel scans | File lock prevents duplicate extraction runs |
| Platform file open | macOS: `open`, Linux: `xdg-open`, Windows: not supported |

---

## 12. Key File Index

| File | Role |
|------|------|
| `NOTION DIARY FETCHER/api/main.py` | FastAPI app — mounts all routers |
| `NOTION DIARY FETCHER/config.toml` | All configuration |
| `NOTION DIARY FETCHER/src/notion_fetcher/client.py` | Notion API auth + pagination |
| `NOTION DIARY FETCHER/src/notion_fetcher/database.py` | SQLite schema + upsert logic |
| `narrative_warehouse/stage1_extractor.py` | Diary → story_nodes |
| `narrative_warehouse/stage2_synthesizer.py` | story_nodes → weekly_index + threads |
| `frameworks/instagram_frameworks/extract_reel.py` | .mp4 → reel_frameworks |
| `frameworks/instagram_frameworks/script_writer.py` | story + reel_framework → script |
| `frameworks/linkedin_frameworks/extract_linkedin.py` | .txt → frameworks |
| `content_writer/api_routes.py` | /content-writer router |
| `shared/shared/logger.py` | Logger factory |
| `frontend/src/components/ContentWriter.jsx` | LinkedIn content UI |
| `frontend/src/components/ReelWriter.jsx` | Reel script UI |
| `frontend/src/components/NarrativeDashboard.jsx` | Narrative insights UI |

*Part 1 covers data model. Part 2 covers pipeline stages and API.*
