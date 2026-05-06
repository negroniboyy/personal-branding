# Content Writer Implementation Log

## Milestone: Part 1 — Backend Scaffold
**Status:** DONE — 2026-05-01

### Files created
| File | Status |
|------|--------|
| `content_writer/__init__.py` | done |
| `content_writer/models.py` | done — StoryNode, Framework, ContentDraft, Req/Result dataclasses |
| `content_writer/db.py` | done — get_connection(), run_migration() (CREATE IF NOT EXISTS content_drafts) |
| `content_writer/repository.py` | done — get_story_nodes, get_frameworks, get_chunks_for_story, get_latest_weekly_index, save_draft, get_drafts, get_draft |
| `content_writer/recommender.py` | done — score_stories (worth_score + weekly bonus + idea bonus), score_frameworks |
| `content_writer/prompt_builder.py` | done — build_prompt, 12k char cap |
| `content_writer/llm_client.py` | done — generate_ollama (live), generate_openai/generate_anthropic (501 stubs) |
| `content_writer/service.py` | done — get_recommendations, generate_draft |
| `content_writer/api_routes.py` | done — GET /frameworks, POST /recommendations, POST /generate, GET /drafts, GET /drafts/{id} |

### Files modified
| File | Change |
|------|--------|
| `NOTION DIARY FETCHER/config.toml` | appended [content_writer] block |
| `NOTION DIARY FETCHER/api/main.py` | mounted content_writer_router after narrative_router |

### Known gaps / next steps
- [ ] Part 2: Frontend — ContentWriter.jsx, contentWriterApi.js, App.jsx tab
- [ ] Import sanity check: `uv run python -c "from content_writer.api_routes import router; print('OK')"`
- [ ] Verify frameworks table columns match repository.py query (id, name, hook_type, tone, paragraph_style, cta, argument_pattern, fits_topics)
- [ ] Verify story_nodes table columns match repository.py query
- [ ] Verify chunks table has story_node_id + chunk_index columns