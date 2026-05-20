# PRD — Personal Branding Platform
## Part 2: Pipeline Stages & API Endpoints

---

## 5. Pipeline Stages

### Stage 0 — Notion Diary Sync

**Module:** `NOTION DIARY FETCHER/src/notion_fetcher/sync.py`  
**Trigger:** Manual — `uv run sync` from `NOTION DIARY FETCHER/`  
**LLM:** None

**`run_sync(token, database_id, config)`**
1. `get_all_database_pages(database_id)` → list of Notion page objects (paginated, 100/batch, 0.34s rate limit)
2. Per page: `upsert_page(page)` → writes `pages` row
3. Per page: `get_page_blocks(page_id)` → list of block objects
4. Per page: `upsert_blocks(page_id, blocks)` → writes `blocks` rows with `plain_text` extracted
5. Per page: `chunk_page_blocks(blocks, title, chunk_size_tokens=500, overlap_chars=50)` → list of chunk strings
6. Per page: `upsert_chunks(page_id, chunks)` → writes `chunks` rows
7. `delete_stale_pages(live_page_ids)` → removes deleted pages

**Output:** `pages`, `blocks`, `chunks` tables populated.

---

### Stage 1 — Story Extraction

**Module:** `narrative_warehouse/stage1_extractor.py`  
**Trigger:** POST `/narrative/extract` (or direct CLI)  
**LLM:** Ollama gemma-32k (or MiniMax cloud)

**`run_extraction(provider=None, model=None) → dict`**
1. Query `pages WHERE processed_status = 0`
2. Per page: `build_diary_text(conn, page_id)` → join all `blocks.plain_text`; skip if empty
3. Call `extract_story_variables(diary_text)` via LLM client
4. LLM returns JSON object:

```json
{
  "user_state": "feeling lost after job rejection",
  "conflict_node": "identity-vs-career",
  "desired_outcome": "clear direction on next move",
  "the_bridge": "reframe failure as data, not verdict",
  "thematic_tags": ["career", "identity", "resilience"],
  "worth_score": 0.82,
  "narrative_flag": "Normal"
}
```

5. INSERT into `story_nodes`; UPDATE `pages.processed_status = 1`

**Returns:**
```json
{
  "status": "ok",
  "pages_processed": 12,
  "story_nodes_created": 10,
  "low_potential_count": 2,
  "errors": [],
  "model_used": "gemma-32k:latest",
  "duration_seconds": 47.3
}
```

---

### Stage 2 — Weekly Synthesis

**Module:** `narrative_warehouse/stage2_synthesizer.py`  
**Trigger:** POST `/narrative/synthesize`  
**LLM:** None (rule-based)

**`run_synthesis(week_start=None) → dict`**
1. `get_week_bounds(week_start)` → (Monday, Sunday) ISO dates
2. Query story_nodes in the week window
3. Group nodes by `normalize_conflict_node(conflict_node)`:
   - lowercase → strip special chars → replace spaces with hyphens
   - Display name: capitalize each word, hyphens → spaces
4. Per group: `compute_sentiment_delta(nodes)` = `avg(worth_score of last half) − avg(worth_score of first half)`
5. Per group: `classify_thread_status(occurrence_count, sentiment_delta)`:
   - 1 occurrence → "Emerging"
   - delta ≥ 0.15 → "Closing"
   - else → "Open"
6. UPSERT `threads` (update occurrence_count, status, last_seen if exists)
7. UPSERT `weekly_index` for the week

**Returns:**
```json
{
  "status": "ok",
  "week_index_id": "weekly_2026-05-18",
  "total_entries": 7,
  "thread_count": 3,
  "open_loops": 2,
  "closed_loops": 1,
  "sentiment_delta": 0.12
}
```

---

### Stage 3A — LinkedIn Framework Extraction

**Module:** `frameworks/linkedin_frameworks/extract_linkedin.py`  
**Trigger:** CLI — `uv run python extract_linkedin.py`  
**Input:** `.txt` reference post files in `references/`  
**LLM:** Ollama gemma-32k

**`run_extraction(dry_run=False) → dict`**
1. Load `prompts/extract_linkedin.txt` template
2. Per `.txt` file (≥50 bytes): `inject_post_text(template, post_text)` → full prompt
3. Call LLM → raw YAML string
4. `parse_yaml_with_fallback(response)`:
   - Strip markdown fences
   - Pre-extract `hook.type`, `cta.type`, `fits_topics` to handle LLM escaping issues
   - Fall back to partial parse on YAML errors
5. Validate required fields; normalize nested fields
6. Generate ID: `<filename>-linkedin-<hook_type>-v1`
7. `save_yaml(framework_id, data)` → writes `.yaml` to `frameworks/` folder
8. `insert_db_row(...)` → writes `frameworks` table row

**LLM Output (YAML):**
```yaml
creator: "author_name"
channel: "linkedin"
source_file: "reference.txt"
hook:
  type: "bold_claim"
  first_line: "Most people get this completely wrong."
structure:
  - section: "Setup"
    content: "Here's the common mistake..."
paragraph_style: "short"
whitespace_use: "sparse"
tone: "authoritative"
cta:
  type: "question"
  example: "What do you think is the real problem?"
fits_topics: ["career", "mindset"]
raw_excerpt: "original post text..."
```

---

### Stage 3B — Reel Framework Extraction

**Module:** `frameworks/instagram_frameworks/extract_reel.py`  
**Trigger:** POST `/reels/scan` (or CLI `--file`)  
**Input:** `.mp4` files in `references/`  
**LLM:** Ollama gemma-32k · **Whisper** (transcription) · **PySceneDetect** (scenes)

**`run_extraction(cfg, single_file=None, dry_run=False)`**  
Per video:
1. `get_duration(filepath)` via ffprobe → `float` seconds
2. `get_transcript_segments(filepath, whisper_model)` via Whisper → `[{start, end, text}, ...]` + full text
3. `get_scene_intervals(filepath, mode, threshold, duration)` via PySceneDetect → `[(start_sec, end_sec), ...]`
4. `compute_hook_silence(segments)` → seconds before first word
5. `build_context_block(duration, scenes, segments, hook_silence)` → formatted string for LLM
6. Inject into `prompts/extract_reel.txt` → LLM prompt
7. Call LLM → raw YAML
8. `parse_yaml_with_fallback(response)` (same as LinkedIn)
9. Validate: hook.type, cta.type, pacing, fits_topics, structure
10. `save_yaml(...)` + `insert_db_row(...)` for `reel_frameworks`
11. On success: delete source `.mp4`; on failure: move to `references/failed/`

**LLM Output (YAML):**
```yaml
creator: "reference_creator"
source_file: "creator_video.mp4"
hook:
  type: "story_open"
  first_line: "Two years ago I almost quit."
structure:
  - scene: 1
    duration: "3.2s"
    content: "Creator addresses camera directly, no text overlay"
pacing: "fast"
tone: "energetic"
cta:
  type: "follow"
  verbal: "Follow for more frameworks like this."
fits_topics: ["entrepreneurship", "resilience"]
```

---

### Stage 4A — LinkedIn Content Generation

**Module:** `content_writer/api_routes.py`  
**Trigger:** POST `/content-writer/generate`  
**LLM:** Ollama gemma3

**`score_stories(nodes, weekly_index, idea_prompt) → sorted list`**
- Base: `worth_score`
- +2.0 if node tags overlap with current week's thread themes
- +1.0 if node tags match words in `idea_prompt`

**`score_frameworks(frameworks, story, idea_prompt) → sorted list`**
- Score = count of `fits_topics` overlapping story tags
- +1.0 if a framework topic appears in `idea_prompt`

**`build_prompt(story, framework, chunks, idea_prompt, max_source_chars) → str`**
- Sections: story narrative (user_state, conflict, outcome, bridge, tags) + framework spec (hook, structure, tone, cta) + idea + source context (truncated chunks)

**Output:** `content_drafts` row + generated text

---

### Stage 4B — Reel Script Generation

**Module:** `frameworks/instagram_frameworks/script_writer.py` + reel API routes  
**Trigger:** POST `/reels/generate`  
**LLM:** Ollama gemma-32k

**`build_script_prompt(story, framework, idea_prompt, template) → str`**
- Sections: story narrative + reel framework (duration, hook, pacing, scene structure, CTA) + idea

**Output:** `reel_scripts` row + generated script text

---

## 6. API Endpoints

All on `http://localhost:8000`.

### 6.1 Health

| Method | Path | Response |
|--------|------|----------|
| GET | `/health` | `{status: "ok"}` |

### 6.2 Diary Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pages` | All pages, newest first. `[{id, title, created_time, last_edited_time, url}]` |
| GET | `/pages/{page_id}` | Single page + blocks. `{id, title, created_time, url, blocks: [{block_type, plain_text, position}]}` |

### 6.3 Narrative Warehouse

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/narrative/extract` | `{provider?, model?}` | `{status, pages_processed, story_nodes_created, low_potential_count, errors, model_used, duration_seconds}` |
| POST | `/narrative/synthesize` | `{week_start?}` | `{status, week_index_id, total_entries, thread_count, open_loops, closed_loops, sentiment_delta}` |
| GET | `/narrative/story-nodes` | `?since&until&min_score&narrative_flag&limit&offset` | `{items: [...], total, limit, offset}` |
| PUT | `/narrative/story-nodes/{node_id}` | any story_node fields | Updated story_node object |
| GET | `/narrative/weekly-index` | `?limit=10` | `{items: [...]}` |
| GET | `/narrative/threads` | `?status&limit` | `{items: [...]}` |

### 6.4 Content Writer (LinkedIn)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/content-writer/recommendations` | `{idea_prompt?, top_n}` | `{stories: [...], frameworks: [...]}` |
| POST | `/content-writer/generate` | `{story_node_id, framework_id, idea_prompt?, provider?, model?}` | `{draft_id, generated_text, story_node_id, framework_id, model_used}` |
| GET | `/content-writer/frameworks` | — | All frameworks array |
| GET | `/content-writer/drafts` | — | Recent 20 drafts |
| GET | `/content-writer/drafts/{id}` | — | Single draft |

### 6.5 Reels (Instagram)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/reels/recommendations` | `{idea_prompt?, top_n}` | `{stories: [...], frameworks: [...]}` |
| POST | `/reels/generate` | `{story_node_id, framework_id, idea_prompt?}` | `{script_id, generated_text, story_node_id, framework_id, model_used, created_at}` |
| GET | `/reels/frameworks` | — | All reel_frameworks |
| GET | `/reels/scripts` | — | Recent 50 scripts |
| GET | `/reels/scripts/{id}` | — | Single script |
| POST | `/reels/scan` | — | `{processed, succeeded: [...], failed: [...]}` |
| POST | `/reels/open-references` | — | `{opened, path, platform}` |

*See Part 3 for Frontend tabs, API client modules, logging, and error handling.*
