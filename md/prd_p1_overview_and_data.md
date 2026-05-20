# PRD — Personal Branding Platform
## Part 1: Overview, Architecture & Data Model

**Version:** v1.5 | **Date:** 2026-05-20 | **Stack:** Python 3.12 · uv · FastAPI · React+Vite · SQLite · Ollama · Whisper · PySceneDetect

---

## 1. Purpose

An end-to-end personal content pipeline. It syncs a Notion diary, extracts narrative story nodes via LLM, synthesizes weekly insights, and generates LinkedIn posts and Instagram reel scripts by combining personal stories with reference content frameworks.

---

## 2. System Architecture

```
NOTION DIARY
    │
    ▼
[Stage 0] Notion Sync ──────────────────────────────────────────
    │  pages · blocks · chunks tables
    │
    ▼
[Stage 1] Story Extraction (LLM)
    │  story_nodes table
    │
    ▼
[Stage 2] Weekly Synthesis (rule-based)
    │  weekly_index · threads tables
    │
    ├──────────────────────────┐
    ▼                          ▼
[Stage 3A] LinkedIn FW     [Stage 3B] Reel FW
 .txt → frameworks table    .mp4 → reel_frameworks table
    │                          │
    ▼                          ▼
[Stage 4A] LinkedIn Gen    [Stage 4B] Reel Script Gen
 content_drafts table       reel_scripts table
    │                          │
    ▼                          ▼
 Frontend: ContentWriter   Frontend: ReelWriter
```

**Backend:** FastAPI on `localhost:8000`  
**Frontend:** React+Vite on `localhost:5173`  
**LLM:** Ollama (local) — gemma-32k (extraction/scripts), gemma3 (content gen)  
**Vision (v2, disabled):** Anthropic Claude for reel frame analysis

---

## 3. Database Schema (SQLite)

All tables in `NOTION DIARY FETCHER/data/notion_diary.db`.

### 3.1 `pages`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | Notion page ID |
| title | TEXT | |
| created_time | TEXT | ISO 8601 |
| last_edited_time | TEXT | |
| url | TEXT | |
| raw_properties_json | TEXT | |
| processed_status | INTEGER | 0=unprocessed, 1=extracted |

### 3.2 `blocks`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | |
| page_id | TEXT FK→pages | Indexed |
| block_type | TEXT | paragraph, heading_1, etc. |
| plain_text | TEXT | Extracted text |
| raw_block_json | TEXT | |
| position | INTEGER | Order within page |

### 3.3 `chunks`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | |
| page_id | TEXT FK→pages | Indexed |
| chunk_index | INTEGER | Sequence within page |
| chunk_text | TEXT | 500-token window, 50-char overlap |

### 3.4 `story_nodes`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `sn_<uuid>` |
| page_id | TEXT UNIQUE | Source page |
| created_time | TEXT | Inherited from diary page |
| user_state | TEXT | LLM: emotional/mental state |
| conflict_node | TEXT | LLM: core challenge (indexed) |
| desired_outcome | TEXT | LLM: goal state |
| the_bridge | TEXT | LLM: transformation path |
| thematic_tags | TEXT JSON | Array of topic strings |
| worth_score | REAL | 0–1 narrative value (indexed) |
| narrative_flag | TEXT | "Normal" or "Low Narrative Potential" |
| llm_model_used | TEXT | |
| processed_at | TEXT | |

### 3.5 `weekly_index`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `weekly_<YYYY-MM-DD>` |
| week_start | TEXT UNIQUE | Monday ISO date (indexed) |
| week_end | TEXT | Sunday ISO date |
| total_entries | INTEGER | Story nodes in week |
| thread_count | INTEGER | Distinct conflict clusters |
| open_loops | INTEGER | Emerging+Open+Closing threads |
| closed_loops | INTEGER | Resolved threads |
| sentiment_delta | REAL | `avg(late half worth) − avg(early half worth)` |
| thread_summary_json | TEXT JSON | Array of thread objects |
| generated_at | TEXT | |

### 3.6 `threads`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `thread_<uuid>` |
| conflict_node | TEXT UNIQUE | Normalized key |
| display_name | TEXT | Human-readable label |
| first_seen | TEXT | ISO date |
| last_seen | TEXT | ISO date |
| occurrence_count | INTEGER | |
| current_status | TEXT | Open · Closing · Emerging · Closed |
| closed_week_start | TEXT | Week it resolved (nullable) |

### 3.7 `frameworks`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `<filename>-linkedin-<hook_type>-v1` |
| creator | TEXT | |
| channel | TEXT | Default 'linkedin' |
| source_file | TEXT | Original .txt filename |
| hook_type | TEXT | bold_claim · question · story_open · stat · pain_point · contrarian |
| hook_first_line | TEXT | Opening hook copy |
| structure_json | TEXT JSON | Array of {section, content} |
| paragraph_style | TEXT | short · medium · long |
| whitespace_use | TEXT | sparse · moderate · dense |
| tone | TEXT | authoritative · conversational · humorous |
| cta_type | TEXT | question · soft_sell · save_this · follow · none |
| cta_example | TEXT | |
| fits_topics | TEXT JSON | Array of theme strings |
| performance_notes | TEXT | |
| raw_excerpt | TEXT | |
| yaml_path | TEXT | |
| created_at | TEXT | |

### 3.8 `reel_frameworks`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `<filename>-instagram-<hook_type>-v1` |
| creator | TEXT | |
| channel | TEXT | Default 'instagram_reel' |
| source_file | TEXT | Original .mp4 filename |
| duration_sec | REAL | Video length |
| scene_count | INTEGER | PySceneDetect output |
| scene_intervals | TEXT JSON | `[(start_sec, end_sec), ...]` |
| hook_type | TEXT | Same types as frameworks |
| hook_verbal | TEXT | Spoken opening line |
| hook_silence_sec | REAL | Pre-speech silence |
| structure_json | TEXT JSON | Array of {scene, duration, content} |
| pacing | TEXT | fast · medium · slow |
| tone | TEXT | |
| cta_type | TEXT | |
| cta_verbal | TEXT | Spoken CTA |
| fits_topics | TEXT JSON | |
| transcript_json | TEXT JSON | `[{start, end, text}, ...]` |
| transcript_text | TEXT | Full flat transcript |
| visual_notes | TEXT | v2: frame analysis (disabled) |
| performance_notes | TEXT | |
| yaml_path | TEXT | |
| created_at | TEXT | |

### 3.9 `content_drafts`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| story_node_id | INTEGER FK→story_nodes | |
| framework_id | INTEGER FK→frameworks | |
| idea_prompt | TEXT | User's framing hint |
| generated_text | TEXT | Final LinkedIn post |
| model_used | TEXT | |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### 3.10 `reel_scripts`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| story_node_id | TEXT | FK→story_nodes |
| framework_id | TEXT | FK→reel_frameworks |
| idea_prompt | TEXT | |
| generated_text | TEXT | Final video script |
| model_used | TEXT | |
| duration_target_sec | REAL | |
| created_at | TEXT | |

---

## 4. Configuration (`NOTION DIARY FETCHER/config.toml`)

```toml
[database]
path = "data/notion_diary.db"

[sync]
rate_limit_delay = 0.34        # seconds between Notion API calls
chunk_size_tokens = 500
chunk_overlap_chars = 50

[notion]
page_size = 100

[narrative_warehouse]
llm_provider = "ollama"        # or "minimax"
llm_model = "gemma-32k:latest"

[ollama]
base_url = "http://localhost:11434"
default_model = "gemma-32k:latest"

[content_writer]
ollama_model = "gemma3:latest"
ollama_host = "http://localhost:11434"
max_source_chars = 12000
default_story_limit = 20

[reel_extractor]
whisper_model = "base"
scenedetect_mode = "adaptive"
content_threshold = 20.0
min_transcript_chars = 20

[reel_extractor.vision]
enabled = false                # v2 — disabled in v1.5
provider = "anthropic"
model = "claude-sonnet-4-6"

[script_writer]
top_n_stories = 5
top_n_frameworks = 3
short_reel_threshold_sec = 15

[logger]
log_dir = "logs"
level = "INFO"
retention_days = 7
```

*See Part 2 for pipeline stages and API endpoints.*
