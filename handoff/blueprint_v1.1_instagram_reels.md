# Blueprint: Instagram Reels Framework Extractor + Script Writer (v1.1)
**Phase 3** — `handoff/blueprint_v1.1_instagram_reels.md`

---

## Context
Phase 2 built the LinkedIn framework extractor (text → YAML → DB). Phase 3 mirrors that pattern for Instagram Reels but adds three local pre-processing steps (Whisper → **timestamped transcript segments**, PySceneDetect → cut intervals, ffprobe → duration) before a **text-only** Ollama LLM identifies the structural framework. A separate `script_writer.py` CLI then matches story_nodes from the DB against reel frameworks and generates a video script.

**Constraint that shaped this revision:** Gemma is text-only. The LLM cannot see the video. In **v1.1** anything visual must come from (a) silence gaps in the timestamped transcript, (b) cut intervals from PySceneDetect, or (c) **manual user notes** typed into a `visual_notes` field after extraction.

**v2 (deferred):** introduce a vision-capable cloud LLM tier (Google Gemini 2.x or Anthropic Claude Sonnet 4.6) that reads sampled video frames and writes structured visual descriptions back into the same `visual_notes` column. This blueprint plants the hooks so v2 only adds, never refactors. See "v2 Vision Hooks" section below.

---

## Affected Files (new)
```
frameworks/instagram_frameworks/
  extract_reel.py         # CLI: video → timestamped transcript + scene intervals + duration → LLM → reel_frameworks table
  script_writer.py        # CLI: story_nodes + reel_frameworks → LLM → reel_scripts table
  llm_client.py           # Ollama client; reads model from config.toml
  schema.yaml             # documentation-only; not imported
  prompts/
    extract_reel.txt      # LLM prompt: timestamped transcript + cuts → YAML framework
    script_writer.txt     # LLM prompt: story + framework → scene-by-scene video script
  references/             # input .mp4 files (user drops reels here)
  frameworks/             # output .yaml files per reel
    failed/               # raw LLM output OR pre-LLM diagnostic when extraction fails
```

### Files modified
```
NOTION DIARY FETCHER/config.toml   # add [reel_extractor] and [script_writer] sections
```

---

## Prerequisites (not installed — install before running)
```bash
brew install ffmpeg                          # provides ffprobe
uv add openai-whisper                        # transcript
uv add scenedetect[opencv]                   # scene cuts
ollama pull gemma-32k:latest                 # local LLM
```
Whisper default model: `base` (overridable via `--whisper-model` flag and `config.toml`).

---

## DB Schema

### New table: `reel_frameworks`
```sql
CREATE TABLE IF NOT EXISTS reel_frameworks (
    id                TEXT PRIMARY KEY,            -- e.g. "1-instagram-story_open-v1"
    creator           TEXT NOT NULL,
    channel           TEXT NOT NULL DEFAULT 'instagram_reel',
    source_file       TEXT NOT NULL,               -- original .mp4 filename
    duration_sec      REAL NOT NULL,
    scene_count       INTEGER NOT NULL,
    scene_intervals   TEXT NOT NULL,               -- JSON: [[start, end], ...] in seconds
    hook_type         TEXT NOT NULL,               -- bold_claim | question | story_open | stat | pain_point | contrarian
    hook_verbal       TEXT,                        -- first spoken sentence (from segments[0])
    hook_silence_sec  REAL,                        -- pre-speech silence at t=0; signal of visual hook intent
    structure_json    TEXT NOT NULL,               -- JSON: [{beat, start_sec, end_sec, description}]
    pacing            TEXT NOT NULL,               -- fast | medium | slow (LLM-derived from cut density)
    tone              TEXT NOT NULL,
    cta_type          TEXT NOT NULL,               -- question | soft_sell | follow | save | none
    cta_verbal        TEXT,
    fits_topics       TEXT NOT NULL,               -- JSON array of 3-5 nouns
    transcript_json   TEXT NOT NULL,               -- JSON: [{start, end, text}, ...] from Whisper
    transcript_text   TEXT NOT NULL,               -- flattened plain text (for FTS later)
    visual_notes      TEXT DEFAULT '',             -- user-edited manual notes; LLM never writes here
    performance_notes TEXT DEFAULT '',
    yaml_path         TEXT NOT NULL,
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rfw_hook_type ON reel_frameworks(hook_type);
CREATE INDEX IF NOT EXISTS idx_rfw_creator   ON reel_frameworks(creator);
CREATE INDEX IF NOT EXISTS idx_rfw_duration  ON reel_frameworks(duration_sec);
```
**Hook enum is verbal-only** — `visual_hook` removed because a text LLM cannot reliably classify it. The `hook_silence_sec` numeric field is the proxy: if non-zero, the reel opens with B-roll/visual.

`visual_notes` is a user-managed field. The LLM never populates it; the user fills it in manually via SQL or a future UI tab using their own observations.

### New table: `reel_scripts`
```sql
CREATE TABLE IF NOT EXISTS reel_scripts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    story_node_id   INTEGER NOT NULL,
    framework_id    TEXT NOT NULL,                 -- FK → reel_frameworks.id
    idea_prompt     TEXT,
    generated_text  TEXT NOT NULL,
    model_used      TEXT NOT NULL,
    duration_target_sec REAL,                      -- copied from framework at generation time
    created_at      TEXT NOT NULL
);
```

---

## Config additions — `NOTION DIARY FETCHER/config.toml`
```toml
[reel_extractor]
whisper_model     = "base"           # tiny | base | small | medium | large
scenedetect_mode  = "adaptive"       # adaptive | content
content_threshold = 20.0             # only used when scenedetect_mode = "content"
ollama_model      = "gemma-32k:latest"
ollama_endpoint   = "http://localhost:11434"
min_transcript_chars = 20            # below this → route to failed/

[script_writer]
ollama_model      = "gemma-32k:latest"
ollama_endpoint   = "http://localhost:11434"
top_n_stories     = 5
top_n_frameworks  = 3
short_reel_threshold_sec = 15        # warn when picking stories with >2 conflict nodes

# v2 placeholder — wired but disabled in v1.1
[reel_extractor.vision]
enabled           = false            # v1.1 keeps this OFF; v2 flips to true
provider          = "anthropic"      # anthropic | google
model             = "claude-sonnet-4-6"   # or "gemini-2.5-pro" for google
api_key_env       = "ANTHROPIC_API_KEY"   # or "GOOGLE_API_KEY"
frame_sample_count = 6               # frames to extract per reel for vision pass
frame_strategy    = "scene_midpoints" # scene_midpoints | uniform | hook_focused
```

---

## Module Logic

### `llm_client.py` — Ollama client
```
llm_client.py — reads Ollama config from config.toml; provides generic prompt completion
  Functions:
    load_config(section: str) -> dict
      Reads config.toml (path resolved relative to this file). Returns the named section.
    complete(prompt: str, section: str = "reel_extractor", dry_run: bool = False) -> str
      Routes to Ollama at configured endpoint with configured model.
    inject(template: str, **placeholders: str) -> str
      Replaces {{KEY}} tokens in template with provided values; raises if any token left unfilled.
  Key rules:
    - Generic vs. linkedin's inject_post_text(); supports multiple placeholders for script_writer.
    - Timeout 180s. On ConnectError print "ollama serve not running" and exit 1.
    - No fallback to cloud yet (placeholder tier returns NotImplementedError).
  Calls: httpx, tomllib (stdlib in 3.11+), pathlib
```

### `extract_reel.py` — video → reel_frameworks table
```
extract_reel.py — orchestrate ffprobe + whisper + scenedetect + LLM into one row per reel
  Functions:
    init_db(conn) -> None
      Creates reel_frameworks table + indexes; idempotent.
    get_duration(filepath: Path) -> float
      Calls: subprocess.run(["ffprobe","-v","quiet","-print_format","json","-show_format",path])
      Returns: float(json["format"]["duration"])
      Key rule: raises RuntimeError("ffprobe not found") if FileNotFoundError.
    get_transcript_segments(filepath: Path, model_name: str) -> tuple[list[dict], str]
      Calls: whisper.load_model(model_name).transcribe(str(filepath))
      Returns: (segments, full_text) where segments = [{"start": float, "end": float, "text": str}, ...]
      Key rule: returns ([], "") on empty audio; caller checks min_transcript_chars.
    get_scene_intervals(filepath: Path, mode: str, threshold: float) -> list[tuple[float, float]]
      Calls: scenedetect.detect(path, AdaptiveDetector()) OR ContentDetector(threshold=threshold)
      Returns: [(start.get_seconds(), end.get_seconds()), ...]
      Key rule: returns [(0.0, duration_sec)] if list is empty.
    compute_hook_silence(segments: list[dict]) -> float
      Returns segments[0]["start"] if segments else 0.0. Used as visual-hook proxy.
    build_context_block(duration: float, scene_intervals: list, segments: list, hook_silence: float) -> str
      Pure string assembly. Format:
        DURATION: 12.3s
        SCENES: [(0.00, 2.10), (2.10, 8.40), (8.40, 12.30)]
        HOOK_SILENCE_SEC: 1.20
        TIMESTAMPED_TRANSCRIPT:
          [0.00–2.10] "Stop scrolling."
          [2.10–8.40] "I built this in a weekend..."
    validate(data: dict) -> list[str]
      Required: creator, source_file, hook.type, hook.first_line, structure (non-empty list with start_sec/end_sec/description),
                pacing in {fast,medium,slow}, tone, cta.type, fits_topics (3-5 items).
      Returns list of missing/invalid fields.
    generate_framework_id(source_file: str, hook_type: str) -> str
      Pattern: "{stem}-instagram-{hook_type}-v1". Note: INSERT OR REPLACE collision behavior is intentional v1 carryover.
    save_yaml(framework_id: str, data: dict) -> Path
    insert_db_row(conn, framework_id: str, data: dict, segments: list, full_text: str,
                  scene_intervals: list, duration: float, hook_silence: float, yaml_path: Path) -> bool
      INSERT OR REPLACE. Serializes scene_intervals + segments + structure + fits_topics as JSON.
    process_file(filepath: Path, cfg: dict, prompt_template: str, conn) -> tuple[str, str]
      Flow:
        1. duration = get_duration(filepath)
        2. segments, full_text = get_transcript_segments(filepath, cfg["whisper_model"])
        3. if len(full_text.strip()) < cfg["min_transcript_chars"]: write to failed/, return "FAILED: transcript too short"
        4. scene_intervals = get_scene_intervals(filepath, cfg["scenedetect_mode"], cfg["content_threshold"])
        5. hook_silence = compute_hook_silence(segments)
        6. ctx = build_context_block(duration, scene_intervals, segments, hook_silence)
        7. raw = llm_client.complete(prompt with ctx injected, section="reel_extractor")
        8. data = parse_yaml_with_fallback(raw)  # reuse the LinkedIn parser pattern
        9. if data is None or validate fails: write raw + ctx to failed/, return "FAILED"
        10. id = generate_framework_id(...); save_yaml; insert_db_row; return id, "OK"
    run_extraction(cfg: dict, single_file: Path | None, dry_run: bool) -> None
      Glob references/*.mp4 (or use single_file). Print summary in LinkedIn format.
  Key rules:
    - All YAML parsing reuses pattern from linkedin_frameworks/extract_linkedin.py (parse_yaml_with_fallback, normalize_*).
    - Failed extractions write BOTH the raw LLM output AND the pre-LLM context block to failed/{stem}.failed.txt
      so the user can inspect whether the model hallucinated or got bad input.
  CLI args:
    --whisper-model    override config (tiny|base|small|medium|large)
    --file PATH        process single .mp4 instead of references/*.mp4
    --dry-run          print assembled prompt(s); no Ollama, no DB writes
  Calls: subprocess, whisper, scenedetect, llm_client, sqlite3, yaml
```

### `script_writer.py` — story + framework → reel_scripts table
```
script_writer.py — match a story_node to a reel framework and generate a scene-by-scene script
  Functions:
    init_db(conn) -> None
      Creates reel_scripts table; idempotent.
    load_story_nodes(conn, limit: int) -> list[dict]
      SELECT id,title,user_state,conflict_node,desired_outcome,the_bridge,thematic_tags,worth_score
      FROM story_nodes ORDER BY worth_score DESC LIMIT ?
    load_reel_frameworks(conn) -> list[dict]
      SELECT * FROM reel_frameworks ORDER BY created_at DESC
    score_frameworks(story: dict, frameworks: list[dict], idea_prompt: str | None) -> list[dict]
      Pure function. Score = |fits_topics ∩ thematic_tags| + (1 if any topic appears in idea_prompt else 0).
      Returns frameworks sorted by score DESC.
    count_conflict_nodes(story: dict) -> int
      Returns number of distinct semicolon- or comma-separated entries in story["conflict_node"].
    build_recommendation_view(stories: list, frameworks_scored: list, short_threshold: float) -> str
      Renders top-N as numbered lists. Each framework line includes duration_sec and a ⚠ marker
      if duration < short_threshold AND any displayed story has count_conflict_nodes > 2.
    pick(stories: list, frameworks: list, story_id_arg: int | None, framework_id_arg: str | None,
         non_interactive: bool) -> tuple[dict, dict]
      Resolution order:
        1. If story_id_arg/framework_id_arg supplied → fetch by id (raises if not found).
        2. If non_interactive → take stories[0], frameworks[0] (top-scored).
        3. Otherwise input("story # [1]: ") and input("framework # [1]: "); empty → top.
    build_script_prompt(story: dict, framework: dict, idea_prompt: str | None,
                        prompt_template: str) -> str
      Injects three placeholders:
        {{STORY}}     → formatted block of story fields
        {{FRAMEWORK}} → duration, hook_type/verbal, structure_json, pacing, tone, cta
        {{IDEA}}      → idea_prompt or "(none provided — improvise from story)"
    generate_script(prompt: str, cfg: dict) -> tuple[str, str]
      Returns (script_text, model_name_used).
    save_script(conn, story_node_id, framework_id, idea_prompt, script, model, duration_target) -> int
      INSERT INTO reel_scripts → returns lastrowid.
    run(idea_prompt: str | None, story_id: int | None, framework_id: str | None,
        dry_run: bool, cfg: dict) -> None
      Flow:
        1. load stories + frameworks
        2. score_frameworks(top story or first, ...)
        3. print build_recommendation_view (skipped when story_id AND framework_id both supplied)
        4. story, framework = pick(...)
        5. prompt = build_script_prompt(...)
        6. if dry_run: print(prompt); return
        7. script, model = generate_script(prompt, cfg)
        8. id = save_script(...)
        9. print f"\n--- reel_scripts.id={id} ---\n{script}"
  Key rules:
    - --dry-run forces non_interactive=True so the run never blocks on input().
    - Recommendation view always shows duration; ⚠ surfaces mismatch but never blocks the user from picking it.
  CLI args:
    --idea TEXT
    --story-id INT
    --framework-id TEXT
    --dry-run
  Calls: sqlite3, llm_client, json
```

### `llm_client.py` v2 hooks (planted in v1.1, no-op until v2)
```
Functions added but unused in v1.1:
  vision_describe(frame_paths: list[Path], prompt: str, cfg: dict) -> str
    If cfg["vision"]["enabled"] is false → raises NotImplementedError("vision tier disabled (v2 feature)")
    Else (v2): dispatch by cfg["vision"]["provider"]:
      - "anthropic" → Anthropic SDK with claude-sonnet-4-6 + image content blocks
      - "google"    → google.generativeai with gemini-2.5-pro + inline_data parts
    Returns: structured visual description string (formatted like the manual visual_notes).
  Key rules:
    - Never called by v1.1 code paths.
    - Reads cfg from [reel_extractor.vision] section.
    - Cost-aware: log "[VISION] est. cost ≈ $X" before each call when v2 ships.
```

### `extract_reel.py` v2 hooks (planted in v1.1, no-op until v2)
```
Functions added but unused in v1.1:
  sample_frames(filepath: Path, scene_intervals: list, count: int, strategy: str) -> list[Path]
    Uses ffmpeg to extract `count` JPEG frames into a tmp dir.
    Strategies: scene_midpoints (one per scene up to count) | uniform | hook_focused (first 3s heavy).
    Returns list of frame paths. Caller cleans up.
  populate_visual_notes_v2(framework_id: str, frame_paths: list[Path], cfg: dict, conn) -> None
    Calls llm_client.vision_describe → UPDATE reel_frameworks SET visual_notes = ? WHERE id = ?
    Only invoked when cfg["vision"]["enabled"] is true (v2).
CLI args added but inert in v1.1:
  --with-vision        v1.1: prints "vision tier disabled in v1.1 — see config.toml" and exits 0
                       v2: triggers the vision pass after the text extraction
```

### `prompts/extract_reel.txt`
- Header: "Return ONLY valid YAML. No fences, no preamble."
- Tells the LLM that the input contains DURATION, SCENES, HOOK_SILENCE_SEC, and a TIMESTAMPED_TRANSCRIPT.
- Explicit rules:
  - Pacing must be inferred from cut density: `fast` if scenes/sec > 0.4, `slow` if < 0.15.
  - `hook.first_line` = the text of segment[0].
  - `structure` beats must reference real timestamps from the input.
  - Do **not** describe visuals; only what is verbally said and where cuts happen.
- Placeholder: `{{REEL_CONTEXT}}`

### `prompts/script_writer.txt`
- Header: "Output a scene-by-scene reel script. Use the format: SCENE n (start–end): VOICEOVER / B-ROLL HINT / ON-SCREEN TEXT."
- Instructs LLM to honor the framework's pacing and total duration.
- Tells LLM to weave in the story's conflict_node + desired_outcome.
- Placeholders: `{{STORY}}`, `{{FRAMEWORK}}`, `{{IDEA}}`

### `schema.yaml` — documentation only
Reference of all reel_frameworks fields and enums. Not imported by any module; lives alongside the LinkedIn schema.yaml as the same kind of artifact.

---

## Data Flow

```
extract_reel.py:
  .mp4 → ffprobe                → duration_sec
       → whisper (segments)     → [{start,end,text},...] + full_text
       → scenedetect (Adaptive) → [(start,end),...]
       → compute_hook_silence   → segments[0].start
       → build_context_block    → {{REEL_CONTEXT}}
       → llm_client.complete    → YAML
       → parse_yaml_with_fallback + validate
       → save_yaml + insert reel_frameworks row
       (failures → failed/{stem}.failed.txt with raw + context)

script_writer.py:
  story_nodes table     → load top-N
  reel_frameworks table → load all
  → score_frameworks (topic overlap + idea hint)
  → recommendation_view (with duration warning)
  → pick (CLI args | non_interactive=top | input())
  → build_script_prompt → {{STORY}} + {{FRAMEWORK}} + {{IDEA}}
  → llm_client.complete → script text
  → reel_scripts row + stdout
```

---

## v2 Vision Hooks — what we plant now, ship later
Goal of this section: v2 must be **additive**, not a refactor.

What v1.1 does today:
1. `[reel_extractor.vision]` section in `config.toml` exists with `enabled = false`.
2. `llm_client.vision_describe()` exists, raises `NotImplementedError` until enabled.
3. `extract_reel.sample_frames()` and `populate_visual_notes_v2()` exist as no-ops behind the same flag.
4. CLI flag `--with-vision` is parsed but prints a "disabled in v1.1" message and exits.
5. `visual_notes` column is the single sink for visual data — manual now, vision-LLM-written in v2.

What v2 needs to do (NOT in this blueprint):
- Flip `enabled = true`, fill `api_key_env`, choose provider.
- Implement the two provider branches in `vision_describe`.
- Add `--with-vision` to actually invoke `populate_visual_notes_v2` after text extraction.
- Add a v2 prompt template (`prompts/vision_describe.txt`) that asks the vision model to fill the same shape that humans write into `visual_notes`.
- Cost guard: print estimate + require `--yes-cost` confirmation if est. > $0.50/run.

---

## Critical files to read before implementation
- `frameworks/linkedin_frameworks/extract_linkedin.py` — reuse `parse_yaml_with_fallback`, `normalize_*`, `validate`, `process_file` pattern, DB-path resolution
- `frameworks/linkedin_frameworks/llm_client.py` — Ollama POST shape, error messages
- `NOTION DIARY FETCHER/config.toml` — existing layout to mirror for new sections
- `content_writer/recommender.py` — scoring style reference (we deliberately keep ours simpler)
- `content_writer/repository.py` — story_nodes column shape

---

## Definition of Done
- [ ] `frameworks/instagram_frameworks/` exists with all files listed above
- [ ] `config.toml` has `[reel_extractor]` and `[script_writer]` sections
- [ ] `extract_reel.py --dry-run --file <sample>` prints the assembled prompt (with timestamps + scene intervals + hook_silence) and exits 0
- [ ] `extract_reel.py --file references/sample.mp4` produces: 1 yaml file + 1 row in `reel_frameworks` (verifiable via `sqlite3 ... "SELECT id, hook_type, duration_sec, hook_silence_sec, scene_count FROM reel_frameworks"`)
- [ ] Empty/silent video routes to `failed/sample.failed.txt` and does **not** insert a row
- [ ] `script_writer.py` lists recommendations including a ⚠ marker on duration/complexity mismatches
- [ ] `script_writer.py --story-id X --framework-id Y --dry-run` prints prompt without prompting for input
- [ ] `script_writer.py --story-id X --framework-id Y` writes one row to `reel_scripts`
- [ ] `visual_notes` column exists, defaults to '', is **never** written by the LLM (verifiable: `SELECT visual_notes FROM reel_frameworks` is empty after extraction)
- [ ] No imports from `content_writer/` — fully standalone
- [ ] v2 vision hooks present but inert: `--with-vision` exits with the v1.1 disabled message; `[reel_extractor.vision]` section is in config.toml with `enabled = false`; `vision_describe()` raises NotImplementedError when called

---

## ⚠️ User Verification Report
Before handoff to Gemma4, confirm each:
1. `ffprobe -version` → prints version
2. `python -c "import whisper; print(whisper.__version__)"` → no error
3. `python -c "import scenedetect; print(scenedetect.__version__)"` → no error
4. `ollama list | grep gemma-32k` → model present (or `ollama pull gemma-32k:latest`)
5. At least one `.mp4` reference reel exists in `frameworks/instagram_frameworks/references/`
6. `sqlite3 "NOTION DIARY FETCHER/data/notion_diary.db" "SELECT count(*) FROM story_nodes"` → > 0
7. After running `extract_reel.py`: open the produced YAML, sanity-check that `structure` timestamps are in `[0, duration_sec]` and `pacing` matches your gut feel for the reel's energy
8. After running `script_writer.py`: confirm the script's number of scenes ≈ framework's `scene_count` and total target duration is mentioned
9. (Manual step you flagged) Open `reel_frameworks` and edit `visual_notes` for each reel with your observations — these will be available for future v1.2 prompts that fold visual cues into script generation
