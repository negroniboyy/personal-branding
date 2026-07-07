# Blueprint v3.4 — Beat-Edit Reference Extraction (Scan Folder wiring)

_2026-07-04 · Planning: Sonnet 5 (inline, collaborative w/ Max) · Execution: Sonnet 5._

## Context

v3.3 (§4/§5) landed reel production tiers, including `beat-edit` — but its template
(`script_writer_beat.txt`) was authored from a single manually-analyzed reference
(`beatedit.MP4`). Max wants the same frame-extraction analysis wired into the existing
"Scan Folder" flow (`POST /reels/scan`) so future beat-edit reference clips get analyzed
automatically and grow a real example pool, rather than staying a one-off manual pass.

**Decisions locked with Max this session:**
- **Detection:** a dedicated subfolder — `references/beat_edit/` — not transcript-length
  heuristics (a beat-edit clip with song lyrics would still produce a long Whisper transcript,
  defeating that signal) and not an LLM classification pass (extra complexity deferred).
  Revisit at §7 GCP VM deploy if remote upload makes foldering impractical.
- **Vision provider:** OpenRouter, not direct Anthropic. `config.toml`'s `[reel_extractor.vision]`
  block was pre-wired for Anthropic but never actually implemented — no `ANTHROPIC_API_KEY`,
  no SDK dependency, and Anthropic's vision pricing is needlessly expensive for this task.
  `OpenRouterClient.chat()` already passes `messages` straight through to the OpenAI-compatible
  endpoint, which fully supports multimodal image content blocks — no new credentials needed.
- **Model cascade (bake-off in `BrandStudio/vision_model_bakeoff_2026-07-04_beat_edit_extraction/`):**
  tested `qwen/qwen3-vl-30b-a3b-instruct`, `google/gemma-4-31b-it`, `google/gemma-4-26b-a4b-it`
  against the same 6 real frames from `beatedit.MP4`. All three read on-screen text identically
  (reliability signal). Only `qwen3-vl` correctly classified the macro cutaway shot; both Gemma
  variants flattened every frame to "wide" — the one thing this template needs right. `gemma-4-31b`
  was also ~6x slower for no quality gain. **Primary: `qwen/qwen3-vl-30b-a3b-instruct`. Secondary:
  `google/gemma-4-26b-a4b-it`** (already proven elsewhere in this project's cascade).

## Definition of Done

1. Dropping an `.mp4` into `references/beat_edit/` and hitting Scan produces a new
   `reel_frameworks` row tagged `video_format='beat_edit'` with a real shot/text beat list —
   no Whisper transcript required, no crash on VO-less audio.
2. `frameworks/picker.py` prefers `video_format='beat_edit'` rows when generating for
   `tier='beat-edit'`, and `video_format='talking_head'` rows otherwise — with a safe fallback
   to the unfiltered pool if the matching-format pool is empty (never blocks generation).
3. `beatedit.MP4` itself gets moved into `references/beat_edit/` and scanned for real, seeding
   the picker pool with one genuine example from day one.
4. Existing scripted-headshot/raw-talking-head generation and the Scan button's frontend are
   unchanged — `ScanJobRow`/`useJob` are already result-shape-agnostic, confirmed no frontend
   edits needed.
5. `python -c "import api.main"` clean · one live end-to-end scan + one live beat-edit
   generation confirm the new pool actually gets picked.

## Affected files

| File | Change |
|------|--------|
| `frameworks/instagram_frameworks/extract_reel.py` | `video_format` column (additive ALTER); new `process_beat_edit_file`, scene-midpoint frame sampling (replaces dead `sample_frames` stub), `validate_beat_edit`, `insert_db_row` gains `video_format` branch; `generate_framework_id` slugifies free-text hook_type |
| `frameworks/instagram_frameworks/prompts/extract_reel_beat.txt` | **NEW** — vision extraction prompt (adapted from the bake-off prompt) |
| `frameworks/instagram_frameworks/llm_client.py` | Remove dead `vision_describe`/`_anthropic_vision`/`_google_vision` stubs; add `complete_vision()` — OpenRouter multimodal call |
| `config/openrouter_models.yaml` | New task `extract_reel_framework_beat_edit`: primary `qwen/qwen3-vl-30b-a3b-instruct`, secondary `google/gemma-4-26b-a4b-it` |
| `NOTION DIARY FETCHER/config.toml` | `[reel_extractor.vision]` simplified to `frame_sample_count`/`frame_strategy` only — model routing now lives in `openrouter_models.yaml` like every other task, not a special-cased provider block |
| `NOTION DIARY FETCHER/api/reel_routes.py` | `scan_references()` also scans `references/beat_edit/`, enqueues `scan_beat_edit_reference_file` jobs |
| `jobs/handlers.py` | New `_handle_scan_beat_edit_reference_file`, registered |
| `frameworks/picker.py` | `pick_framework(..., video_format=None)` filters by format with safe fallback; `_fallback` filters too |
| `frameworks/instagram_frameworks/script_writer.py` | `load_reel_frameworks(conn, video_format=None)` filter param; `_format_framework` branches on `video_format` |
| `jobs/handlers.py::_handle_generate_reel` | passes `video_format` derived from `tier` into `pick_framework` |

## Out of scope

Auto-detection redesign for remote/VM uploads (§7) · vision extraction for talking-head refs
(existing Whisper path untouched) · UI surfacing of `video_format` in Frameworks tab.
