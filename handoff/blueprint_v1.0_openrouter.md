# Blueprint v1.0 — OpenRouter Content Scaffolding

**Phase:** Planning complete → Hand off to Gemma4
**Date:** 2026-05-27
**Feature:** openrouter_writer

---

## State

**Repo summary:** Personal brand monorepo. FastAPI :8000 backend, React 18 frontend, SQLite DB at `NOTION DIARY FETCHER/data/notion_diary.db`. Tables: `story_nodes`, `content_drafts`, `reel_scripts`, `frameworks`, `reel_frameworks`.

**New module:** `content_writer/openrouter_writer.py`

**Affected files:**
- `content_writer/openrouter_writer.py` ← NEW
- `content_writer/api_routes.py` ← add new endpoint
- `NOTION DIARY FETCHER/config.toml` ← add [openrouter] section
- `requirements.txt` / `pyproject.toml` ← add `httpx`

**DO NOT install axios 1.14.1 or 0.30.4**

---

## Logic

### openrouter_writer.py — generates content drafts via OpenRouter API

```
Functions:
  load_voice_dna() -> str
    Reads brandguide/voice_dna.md at repo root
    Returns full file content as string
    Called once per session, cached in module-level var

  build_system_prompt(platform: str) -> str
    Calls load_voice_dna()
    Appends platform-specific instruction:
      LinkedIn: "Write a LinkedIn post."
      IG Reel: "Write a voiceover script for an Instagram Reel."
      IG Static: "Write an Instagram caption."
    Returns combined system prompt string

  build_user_prompt(story_node: dict, framework: dict, platform: str) -> str
    Formats story_node fields (user_state, conflict_node, desired_outcome, thematic_tags)
    Formats framework structure (hook_type, hook_first_line, structure_json)
    Returns structured prompt string (see template below)

  call_openrouter(system: str, user: str, model: str) -> str
    POST https://openrouter.ai/api/v1/chat/completions
    Headers: Authorization: Bearer {OPENROUTER_API_KEY}
    Body: {model, messages: [{role:system,content:system},{role:user,content:user}]}
    Returns response choices[0].message.content
    Raises on non-200 with status + body logged via get_logger("content_writer")

  generate_image(prompt: str, model: str = "black-forest-labs/flux-schnell") -> str
    POST https://openrouter.ai/api/v1/images/generations
    Body: {model, prompt, n:1, size:"1024x1024"}
    Returns image URL string
    Raises on non-200

  save_draft(conn, story_node_id: str, framework_id: int,
             platform: str, generated_text: str, model: str,
             idea_id: str | None = None) -> int
    If platform in ["LinkedIn", "IG Static"]:
      INSERT INTO content_drafts (story_node_id, framework_id, idea_prompt,
        generated_text, model_used, idea_id)
      Returns new row id
    If platform == "IG Reel":
      INSERT INTO reel_scripts (story_node_id, framework_id, idea_prompt,
        generated_text, model_used, duration_target_sec, idea_id)
      duration_target_sec = 65
      Returns new row id
```

**Key rules:**
- API key from env: `OPENROUTER_API_KEY` — never hardcoded
- Default model from config.toml `[openrouter] default_model`
- All HTTP calls use `httpx` (async if in async context, sync otherwise)
- Logger: `get_logger("content_writer")`
- No axios, no node packages for this module

### User prompt template

```
Story node:
- User state: {user_state}
- Conflict: {conflict_node}
- Desired outcome: {desired_outcome}
- Tags: {thematic_tags}

Platform: {platform}
Framework hook: {hook_type} — "{hook_first_line}"
Framework structure: {structure_summary}
Domain: {domain}

Write a draft in Max's voice. Follow the voice DNA exactly.
Use the framework structure as the skeleton.
Do not add CTAs, hashtag blocks, or motivational sign-offs unless the framework explicitly calls for them.
Keep LinkedIn posts under 250 words. Keep Reel scripts under 90 words (spoken word pace).
```

### api_routes.py — new endpoint

```
POST /content-writer/generate
  Body: GenerateRequest {
    story_node_id: str
    framework_id: int         # from frameworks or reel_frameworks table
    platform: str             # "LinkedIn" | "IG Reel" | "IG Static"
    model: str | None         # defaults to config default_model
    generate_image: bool      # default False
    image_prompt: str | None  # required if generate_image=True
  }
  Returns: GenerateResponse {
    draft_id: int
    generated_text: str
    image_url: str | None
    model_used: str
  }
  Calls: openrouter_writer.generate_draft() which orchestrates all steps
  Saves to DB before returning
```

### config.toml additions

```toml
[openrouter]
default_model = "meta-llama/llama-3.1-8b-instruct"
image_model = "black-forest-labs/flux-schnell"
api_base = "https://openrouter.ai/api/v1"
```

---

## Specs

- Python 3.12, `uv` for package management
- `httpx` for HTTP (add to pyproject.toml)
- Logger: `from shared.logger import get_logger` — one call at module top
- Config: use existing `NOTION DIARY FETCHER/config.toml` pattern
- API key: env var only, document in `.env.example`

---

## Definition of Done

- [ ] `openrouter_writer.py` exists with all 5 functions
- [ ] `POST /content-writer/generate` returns a draft and saves to DB
- [ ] Draft appears in `content_drafts` or `reel_scripts` table
- [ ] Image generation works when `generate_image=True`
- [ ] API key never appears in code or logs
- [ ] Logger used (no print for errors)
- [ ] Test: call endpoint with `sn_be9d61978326` + framework id 1 + LinkedIn → get text back

---

## ⚠️ User Verification Report

Before moving to UI wiring, check each item and report what failed:

- [ ] Can call `/content-writer/generate` and get a non-empty response?
- [ ] Is the generated text recognisably in Max's voice (check 3 items from voice_dna side-by-side table)?
- [ ] Does the draft appear in the DB (`content_drafts` table)?
- [ ] Does image generation return a URL when requested?
- [ ] Is OPENROUTER_API_KEY loaded from env, not hardcoded?
