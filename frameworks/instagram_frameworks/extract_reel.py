#!/usr/bin/env python3
"""
Extract Instagram Reel frameworks from .mp4 reference files.
Pipeline: ffprobe → Whisper (timestamped segments) → PySceneDetect → OpenRouter LLM → YAML + reel_frameworks table.
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

import llm_client
from shared.logger import get_logger

logger = get_logger("instagram_frameworks")

SCRIPT_DIR      = Path(__file__).parent.resolve()
REFERENCES_DIR  = SCRIPT_DIR / "references"
PROMPTS_DIR     = SCRIPT_DIR / "prompts"
FRAMEWORKS_DIR  = SCRIPT_DIR / "frameworks"
FAILED_DIR      = FRAMEWORKS_DIR / "failed"
PROMPT_PATH      = PROMPTS_DIR / "extract_reel.txt"
BEAT_PROMPT_PATH = PROMPTS_DIR / "extract_reel_beat.txt"
BEAT_EDIT_REFERENCES_DIR = REFERENCES_DIR / "beat_edit"

DB_PATH = Path(__file__).parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"
if not DB_PATH.exists():
    DB_PATH = Path(__file__).parent.parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

# When set (e.g. PBS_API_BASE=http://100.85.36.42:9000), extracted frameworks are
# POSTed to the remote PBS API instead of written to the local SQLite — extraction
# runs on the Mac (whisper/scenedetect), the DB of record lives on the VM.
REMOTE_API_BASE = os.environ.get("PBS_API_BASE", "").rstrip("/")

HOOK_TYPES   = {"bold_claim", "question", "story_open", "stat", "pain_point", "contrarian"}
CTA_TYPES    = {"question", "soft_sell", "follow", "save", "none"}
PACING_TYPES = {"fast", "medium", "slow"}

REQUIRED_FIELDS = [
    "creator", "source_file", "hook", "structure",
    "pacing", "tone", "cta", "fits_topics",
]

REQUIRED_FIELDS_BEAT_EDIT = [
    "creator", "source_file", "hook_type", "tone",
    "color_system", "shot_pattern", "beats", "fits_topics", "description",
]


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reel_frameworks (
            id                TEXT PRIMARY KEY,
            creator           TEXT NOT NULL,
            channel           TEXT NOT NULL DEFAULT 'instagram_reel',
            source_file       TEXT NOT NULL,
            duration_sec      REAL NOT NULL,
            scene_count       INTEGER NOT NULL,
            scene_intervals   TEXT NOT NULL,
            hook_type         TEXT NOT NULL,
            hook_verbal       TEXT,
            hook_silence_sec  REAL,
            structure_json    TEXT NOT NULL,
            pacing            TEXT NOT NULL,
            tone              TEXT NOT NULL,
            cta_type          TEXT NOT NULL,
            cta_verbal        TEXT,
            fits_topics       TEXT NOT NULL,
            transcript_json   TEXT NOT NULL,
            transcript_text   TEXT NOT NULL,
            visual_notes      TEXT DEFAULT '',
            performance_notes TEXT DEFAULT '',
            description       TEXT DEFAULT '',
            yaml_path         TEXT NOT NULL,
            created_at        TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rfw_hook_type ON reel_frameworks(hook_type);
        CREATE INDEX IF NOT EXISTS idx_rfw_creator   ON reel_frameworks(creator);
        CREATE INDEX IF NOT EXISTS idx_rfw_duration  ON reel_frameworks(duration_sec);
    """)
    for alter in [
        "ALTER TABLE reel_frameworks ADD COLUMN video_format TEXT DEFAULT 'talking_head'",
    ]:
        try:
            conn.execute(alter)
        except Exception:
            pass
    conn.commit()


# ---------------------------------------------------------------------------
# Pre-processing
# ---------------------------------------------------------------------------

def get_duration(filepath: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(filepath.resolve())],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except FileNotFoundError:
        raise RuntimeError("ffprobe not found — run `brew install ffmpeg`")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "(no stderr)"
        raise RuntimeError(f"ffprobe failed on {filepath.name}: {stderr}")


def get_transcript_segments(filepath: Path, model_name: str) -> tuple[list[dict], str]:
    import whisper
    model = whisper.load_model(model_name)
    result = model.transcribe(str(filepath))
    segments = [
        {"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()}
        for s in result.get("segments", [])
    ]
    full_text = result.get("text", "").strip()
    return segments, full_text


def get_scene_intervals(filepath: Path, mode: str, threshold: float, duration: float) -> list[tuple[float, float]]:
    from scenedetect import detect, AdaptiveDetector, ContentDetector
    if mode == "adaptive":
        detector = AdaptiveDetector()
    else:
        detector = ContentDetector(threshold=threshold)
    scene_list = detect(str(filepath), detector)
    if not scene_list:
        return [(0.0, duration)]
    return [(s[0].get_seconds(), s[1].get_seconds()) for s in scene_list]


def compute_hook_silence(segments: list[dict]) -> float:
    if not segments:
        return 0.0
    return round(segments[0]["start"], 3)


# ---------------------------------------------------------------------------
# Context block for LLM
# ---------------------------------------------------------------------------

def build_context_block(
    duration: float,
    scene_intervals: list[tuple[float, float]],
    segments: list[dict],
    hook_silence: float,
) -> str:
    scenes_fmt = ", ".join(f"({s:.2f}, {e:.2f})" for s, e in scene_intervals)
    lines = [
        f"DURATION: {duration:.2f}s",
        f"SCENES: [{scenes_fmt}]",
        f"HOOK_SILENCE_SEC: {hook_silence:.2f}",
        "TIMESTAMPED_TRANSCRIPT:",
    ]
    for seg in segments:
        lines.append(f'  [{seg["start"]:.2f}–{seg["end"]:.2f}] "{seg["text"]}"')
    if not segments:
        lines.append("  (no speech detected)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# YAML parsing (mirrors linkedin_frameworks pattern)
# ---------------------------------------------------------------------------

_PRE_EXTRACT_PATTERN = re.compile(
    r'^(hook\.type|hook\.first_line|cta\.type|cta\.verbal|fits_topics)\s*:[ \t]*(.*)',
    re.MULTILINE,
)


def parse_yaml_with_fallback(raw: str) -> dict | None:
    text = raw.strip()
    if not text:
        return None

    text = text.lstrip("```yaml").lstrip("```").strip()
    text = text.removesuffix("```").strip()

    raw_excerpt_value = None
    if "\nraw_excerpt:" in text:
        idx = text.find("\nraw_excerpt:")
        after_key = text[idx + len("\nraw_excerpt:"):]
        stripped_after = after_key.lstrip(" \t")
        if stripped_after.startswith(("|", ">")):
            for line in after_key.split("\n")[1:]:
                stripped = line.strip()
                if stripped:
                    raw_excerpt_value = stripped.lstrip("- ").strip()
                    break
        else:
            raw_excerpt_value = after_key.split("\n")[0].strip()
        text = text[:idx].rstrip()

    pre_extracted: dict[str, str] = {}

    def _capture(m: re.Match) -> str:
        value = m.group(2).strip()
        if value:
            pre_extracted[m.group(1)] = value
            return ""
        return m.group(0)

    text = _PRE_EXTRACT_PATTERN.sub(_capture, text)

    # '@' and '`' are reserved YAML indicator characters — an unquoted "@handle"
    # value (common for social handles like a creator field) breaks the parser.
    text = re.sub(r'^(\s*(?:-\s+)?[A-Za-z_][A-Za-z0-9_]*:\s+)([@`]\S.*)$', r'\1"\2"', text, flags=re.MULTILINE)

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    for key, value in pre_extracted.items():
        if key not in data or data[key] is None:
            data[key] = value

    if raw_excerpt_value is not None:
        data["raw_excerpt"] = raw_excerpt_value

    return data


def _unquote(value: str | None) -> str | None:
    if not value:
        return value
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


def normalize_nested_fields(data: dict) -> None:
    hook_type       = _unquote(data.pop("hook.type", None))
    hook_first_line = _unquote(data.pop("hook.first_line", None))
    existing_hook   = data.get("hook")
    if isinstance(existing_hook, dict):
        if hook_type and "type" not in existing_hook:
            existing_hook["type"] = hook_type
        if hook_first_line and "first_line" not in existing_hook:
            existing_hook["first_line"] = hook_first_line
    elif hook_type or hook_first_line:
        data["hook"] = {"type": hook_type or "", "first_line": hook_first_line or ""}

    cta_type   = _unquote(data.pop("cta.type", None))
    cta_verbal = _unquote(data.pop("cta.verbal", None))
    existing_cta = data.get("cta")
    if isinstance(existing_cta, dict):
        if cta_type and "type" not in existing_cta:
            existing_cta["type"] = cta_type
        if cta_verbal and "verbal" not in existing_cta:
            existing_cta["verbal"] = cta_verbal
    elif cta_type or cta_verbal:
        data["cta"] = {"type": cta_type or "", "verbal": cta_verbal or ""}


def normalize_fits_topics(data: dict) -> None:
    if "fits_topics" in data and isinstance(data["fits_topics"], str):
        val = data["fits_topics"].strip().strip("[]")
        if "," in val:
            topics = [t.strip().strip('"').strip("'") for t in val.split(",")]
        else:
            tokens = re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', val)
            topics = [t[0] or t[1] or t[2] for t in tokens]
        data["fits_topics"] = [t for t in topics if t]


def normalize_source_file(data: dict, fallback: str) -> None:
    sf = data.get("source_file", "")
    if isinstance(sf, list):
        sf = sf[0] if sf else ""
    sf = str(sf).strip() if sf else ""
    if not sf or sf in ("null", "None", "unknown", "N/A"):
        data["source_file"] = fallback
    else:
        data["source_file"] = sf


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(data: dict) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None or data[field] == "":
            missing.append(field)
    hook = data.get("hook")
    if isinstance(hook, dict):
        if not hook.get("type"):
            missing.append("hook.type")
        elif hook["type"] not in HOOK_TYPES:
            missing.append(f"hook.type invalid ({hook['type']})")
        if not hook.get("first_line"):
            missing.append("hook.first_line")
    cta = data.get("cta")
    if isinstance(cta, dict):
        if not cta.get("type") or cta["type"] not in CTA_TYPES:
            missing.append("cta.type")
    pacing = data.get("pacing", "")
    if pacing not in PACING_TYPES:
        missing.append(f"pacing invalid ({pacing!r})")
    fits = data.get("fits_topics")
    if not isinstance(fits, list) or len(fits) < 1:
        missing.append("fits_topics (must be non-empty list)")
    structure = data.get("structure")
    if not isinstance(structure, list) or len(structure) < 1:
        missing.append("structure (must be non-empty list)")
    return missing


def validate_beat_edit(data: dict) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS_BEAT_EDIT:
        if field not in data or data[field] is None or data[field] == "":
            missing.append(field)
    beats = data.get("beats")
    if not isinstance(beats, list) or len(beats) < 1:
        missing.append("beats (must be non-empty list)")
    fits = data.get("fits_topics")
    if not isinstance(fits, list) or len(fits) < 1:
        missing.append("fits_topics (must be non-empty list)")
    return missing


# ---------------------------------------------------------------------------
# ID / persistence
# ---------------------------------------------------------------------------

def generate_framework_id(source_file: str, hook_type: str) -> str:
    stem = Path(source_file).stem.lower().replace(" ", "-")
    # preserve underscores so existing hook_type values (e.g. "bold_claim") keep
    # generating identical IDs; only punctuation/spaces from free-text beat-edit
    # hook_type phrases get collapsed to hyphens.
    hook_slug = re.sub(r"[^a-z0-9_]+", "-", hook_type.lower()).strip("-")[:30]
    return f"{stem}-instagram-{hook_slug}-v1"


def save_yaml(framework_id: str, data: dict) -> Path:
    FRAMEWORKS_DIR.mkdir(parents=True, exist_ok=True)
    path = FRAMEWORKS_DIR / f"{framework_id}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path


def _persist_row(conn: sqlite3.Connection, row: dict) -> bool:
    """Local SQLite insert, or POST to the remote PBS API when PBS_API_BASE is set."""
    try:
        if REMOTE_API_BASE:
            import httpx
            resp = httpx.post(f"{REMOTE_API_BASE}/frameworks/reel/ingest", json=row, timeout=30)
            resp.raise_for_status()
            return True
        cols = ", ".join(row)
        marks = ",".join("?" * len(row))
        conn.execute(
            f"INSERT OR REPLACE INTO reel_frameworks ({cols}) VALUES ({marks})",
            tuple(row.values()),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("Persist failed for %s: %s", row.get("id"), e)
        return False


def insert_db_row(
    conn: sqlite3.Connection,
    framework_id: str,
    data: dict,
    segments: list[dict],
    full_text: str,
    scene_intervals: list[tuple[float, float]],
    duration: float,
    hook_silence: float,
    yaml_path: Path,
) -> bool:
    def _s(v) -> str:
        if v is None:
            return ""
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        return str(v)

    hook = data.get("hook", {}) or {}
    cta  = data.get("cta", {}) or {}
    now  = datetime.now(timezone.utc).isoformat()

    row = {
        "id": framework_id,
        "creator": _s(data.get("creator", "unknown")),
        "channel": "instagram_reel",
        "source_file": _s(data.get("source_file", "")),
        "duration_sec": duration,
        "scene_count": len(scene_intervals),
        "scene_intervals": json.dumps([[s, e] for s, e in scene_intervals]),
        "hook_type": _s(hook.get("type", "")),
        "hook_verbal": _s(hook.get("first_line", "")),
        "hook_silence_sec": hook_silence,
        "structure_json": json.dumps(data.get("structure", [])),
        "pacing": _s(data.get("pacing", "")),
        "tone": _s(data.get("tone", "")),
        "cta_type": _s(cta.get("type", "")),
        "cta_verbal": _s(cta.get("verbal", "")),
        "fits_topics": json.dumps(data.get("fits_topics", [])),
        "transcript_json": json.dumps(segments),
        "transcript_text": full_text,
        "visual_notes": "",
        "performance_notes": _s(data.get("performance_notes", "")),
        "description": _s(data.get("description", "")),
        "yaml_path": str(yaml_path),
        "created_at": now,
    }
    return _persist_row(conn, row)


def insert_db_row_beat_edit(
    conn: sqlite3.Connection,
    framework_id: str,
    data: dict,
    scene_intervals: list[tuple[float, float]],
    duration: float,
    yaml_path: Path,
) -> bool:
    """Beat-edit rows have no verbal hook/CTA and no Whisper transcript — the on-screen
    text sequence (`beats[].text_guess`) stands in for both, so keyword search over
    `transcript_text` still works uniformly across both video_formats."""
    def _s(v) -> str:
        if v is None:
            return ""
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        return str(v)

    beats = data.get("beats", []) or []
    on_screen_text = " / ".join(
        b.get("text_guess", "") for b in beats if isinstance(b, dict) and b.get("text_guess")
    )
    visual_notes = (
        f"color_system: {data.get('color_system', '')} | shot_pattern: {data.get('shot_pattern', '')}"
    )
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "id": framework_id,
        "creator": _s(data.get("creator", "unknown")),
        "channel": "instagram_reel",
        "source_file": _s(data.get("source_file", "")),
        "duration_sec": duration,
        "scene_count": len(scene_intervals),
        "scene_intervals": json.dumps([[s, e] for s, e in scene_intervals]),
        "hook_type": _s(data.get("hook_type", "")),
        "hook_verbal": "",
        "hook_silence_sec": None,
        "structure_json": json.dumps(beats),
        "pacing": "fast",
        "tone": _s(data.get("tone", "")),
        "cta_type": "",
        "cta_verbal": "",
        "fits_topics": json.dumps(data.get("fits_topics", [])),
        "transcript_json": "[]",
        "transcript_text": on_screen_text,
        "visual_notes": visual_notes,
        "performance_notes": "",
        "description": _s(data.get("description", "")),
        "yaml_path": str(yaml_path),
        "created_at": now,
        "video_format": "beat_edit",
    }
    return _persist_row(conn, row)


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

def _write_failed(stem: str, context_block: str, raw_llm: str) -> None:
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    path = FAILED_DIR / f"{stem}.failed.txt"
    path.write_text(
        f"=== PRE-LLM CONTEXT ===\n{context_block}\n\n=== RAW LLM OUTPUT ===\n{raw_llm}",
        encoding="utf-8",
    )


def process_file(
    filepath: Path,
    cfg: dict,
    prompt_template: str,
    conn: sqlite3.Connection,
) -> tuple[str, str]:
    stem = filepath.stem

    if not filepath.exists():
        return filepath.name, f"FAILED: file not found at {filepath.resolve()}"

    try:
        duration = get_duration(filepath)
    except RuntimeError as e:
        _write_failed(stem, f"filepath: {filepath.resolve()}", str(e))
        return filepath.name, f"FAILED: {e}"

    segments, full_text = get_transcript_segments(filepath, cfg["whisper_model"])
    if len(full_text.strip()) < cfg["min_transcript_chars"]:
        _write_failed(stem, f"DURATION: {duration:.2f}s\n(transcript too short)", full_text)
        return filepath.name, f"FAILED: transcript too short ({len(full_text.strip())} chars)"

    scene_intervals = get_scene_intervals(
        filepath, cfg["scenedetect_mode"], cfg["content_threshold"], duration
    )
    hook_silence = compute_hook_silence(segments)
    ctx = build_context_block(duration, scene_intervals, segments, hook_silence)

    prompt = llm_client.inject(prompt_template, REEL_CONTEXT=ctx)
    raw, _model_used = llm_client.complete(prompt, section="reel_extractor")

    data = parse_yaml_with_fallback(raw)
    if data is None:
        _write_failed(stem, ctx, raw)
        return filepath.name, "FAILED: unparseable YAML"

    normalize_fits_topics(data)
    normalize_source_file(data, filepath.name)
    normalize_nested_fields(data)

    missing = validate(data)
    if missing:
        _write_failed(stem, ctx, raw)
        return filepath.name, f"FAILED: missing fields: {', '.join(missing)}"

    hook_type    = (data.get("hook") or {}).get("type", "unknown")
    framework_id = generate_framework_id(filepath.name, hook_type)
    yaml_path    = save_yaml(framework_id, data)
    db_ok        = insert_db_row(conn, framework_id, data, segments, full_text,
                                  scene_intervals, duration, hook_silence, yaml_path)

    status = "OK" if db_ok else "OK (DB insert warning)"
    return framework_id, status


# ---------------------------------------------------------------------------
# Beat-edit extraction (references/beat_edit/ — vision path, no transcript)
# ---------------------------------------------------------------------------

def choose_scene_subset(
    scene_intervals: list[tuple[float, float]], count: int
) -> list[tuple[float, float]]:
    """Evenly picks up to `count` scenes from the full list. Shared by frame sampling
    and context-block building so the prompt only ever describes scenes the model
    actually gets an image for — otherwise it infers/hallucinates extra beats from a
    scene list it can't see."""
    if len(scene_intervals) <= count:
        return list(scene_intervals)
    step = len(scene_intervals) / count
    return [scene_intervals[int(i * step)] for i in range(count)]


def sample_scene_midpoint_frames(
    filepath: Path,
    chosen_scenes: list[tuple[float, float]],
    tmpdir: Path,
) -> list[Path]:
    """One frame at the midpoint of each given scene — the actual cut points
    PySceneDetect found, i.e. the beats of the edit."""
    if not chosen_scenes:
        return []

    tmpdir.mkdir(parents=True, exist_ok=True)
    frame_paths = []
    for i, (start, end) in enumerate(chosen_scenes):
        midpoint = (start + end) / 2
        out_path = tmpdir / f"frame_{i:02d}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{midpoint:.3f}", "-i", str(filepath),
             "-vframes", "1", "-vf", "scale=360:-1", "-q:v", "3", "-y", str(out_path)],
            check=True,
        )
        frame_paths.append(out_path)
    return frame_paths


def build_beat_edit_context_block(duration: float, chosen_scenes: list[tuple[float, float]]) -> str:
    scenes_fmt = ", ".join(f"({s:.2f}, {e:.2f})" for s, e in chosen_scenes)
    return (
        f"DURATION: {duration:.2f}s\n"
        f"SAMPLED SCENES (one frame per scene below, in order — the ONLY frames you can see): "
        f"[{scenes_fmt}]\n"
        f"(no speech — visual/music-driven)"
    )


def process_beat_edit_file(
    filepath: Path,
    cfg: dict,
    vision_cfg: dict,
    prompt_template: str,
    conn: sqlite3.Connection,
) -> tuple[str, str]:
    stem = filepath.stem

    if not filepath.exists():
        return filepath.name, f"FAILED: file not found at {filepath.resolve()}"

    try:
        duration = get_duration(filepath)
    except RuntimeError as e:
        _write_failed(stem, f"filepath: {filepath.resolve()}", str(e))
        return filepath.name, f"FAILED: {e}"

    scene_intervals = get_scene_intervals(
        filepath, cfg["scenedetect_mode"], cfg["content_threshold"], duration
    )
    chosen_scenes = choose_scene_subset(scene_intervals, vision_cfg["frame_sample_count"])
    ctx = build_beat_edit_context_block(duration, chosen_scenes)

    with tempfile.TemporaryDirectory() as tmp:
        frame_paths = sample_scene_midpoint_frames(filepath, chosen_scenes, Path(tmp))
        if not frame_paths:
            _write_failed(stem, ctx, "(no scenes detected — could not sample frames)")
            return filepath.name, "FAILED: no scenes detected"

        prompt = llm_client.inject(prompt_template, REEL_CONTEXT=ctx)
        raw, _model_used = llm_client.complete_vision(prompt, frame_paths, section="reel_extractor_beat_edit")

    data = parse_yaml_with_fallback(raw)
    if data is None:
        _write_failed(stem, ctx, raw)
        return filepath.name, "FAILED: unparseable YAML"

    normalize_fits_topics(data)
    normalize_source_file(data, filepath.name)

    missing = validate_beat_edit(data)
    if missing:
        _write_failed(stem, ctx, raw)
        return filepath.name, f"FAILED: missing fields: {', '.join(missing)}"

    hook_type    = data.get("hook_type", "unknown")
    framework_id = generate_framework_id(filepath.name, hook_type)
    yaml_path    = save_yaml(framework_id, data)
    db_ok        = insert_db_row_beat_edit(conn, framework_id, data, scene_intervals, duration, yaml_path)

    status = "OK" if db_ok else "OK (DB insert warning)"
    return framework_id, status


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_extraction(cfg: dict, single_file: Path | None, dry_run: bool) -> None:
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    if dry_run:
        ctx = None
        target = single_file or next((p for p in REFERENCES_DIR.iterdir() if p.suffix.lower() == ".mp4"), None)
        if target and target.exists():
            try:
                duration = get_duration(target)
                segments, full_text = get_transcript_segments(target, cfg["whisper_model"])
                scene_intervals = get_scene_intervals(
                    target, cfg["scenedetect_mode"], cfg["content_threshold"], duration
                )
                hook_silence = compute_hook_silence(segments)
                ctx = build_context_block(duration, scene_intervals, segments, hook_silence)
            except Exception as e:
                print(f"[dry-run] Could not process {target.name}: {e} — using synthetic context", file=sys.stderr)
        if ctx is None:
            ctx = (
                "DURATION: 12.34s\n"
                "SCENES: [(0.00, 3.20), (3.20, 8.90), (8.90, 12.34)]\n"
                "HOOK_SILENCE_SEC: 0.80\n"
                "TIMESTAMPED_TRANSCRIPT:\n"
                '  [0.80–3.20] "Stop scrolling. This is the thing nobody tells you."\n'
                '  [3.20–8.90] "I spent three years figuring this out the hard way..."\n'
                '  [8.90–12.34] "Save this. You will need it."'
            )
        prompt = llm_client.inject(prompt_template, REEL_CONTEXT=ctx)
        print(prompt)
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    def _find_mp4s(directory: Path) -> list[Path]:
        return sorted(p for p in directory.iterdir() if p.suffix.lower() == ".mp4")

    files = [single_file] if single_file else _find_mp4s(REFERENCES_DIR)
    if not files:
        logger.error("No .mp4 files found in %s", REFERENCES_DIR)
        conn.close()
        sys.exit(1)

    results = []
    for filepath in files:
        print(f"  Processing {filepath.name} ...", end=" ", flush=True)
        framework_id, status = process_file(filepath, cfg, prompt_template, conn)
        marker = "OK" if status.startswith("OK") else "FAILED"
        print(f"→ {framework_id} [{marker}]")
        results.append((filepath.name, framework_id, status))

    conn.close()

    succeeded = sum(1 for _, _, s in results if s.startswith("OK"))
    failed    = sum(1 for _, _, s in results if s.startswith("FAILED"))
    print(f"\nSummary: {len(results)} processed | {succeeded} OK | {failed} failed")
    if failed:
        print("\nFailed:")
        for name, _, status in results:
            if status.startswith("FAILED"):
                print(f"  {name}: {status}")

    sys.exit(0 if failed == 0 else 1)


def run_beat_edit_extraction(cfg: dict, vision_cfg: dict, single_file: Path | None) -> None:
    prompt_template = BEAT_PROMPT_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    if single_file:
        files = [single_file]
    elif BEAT_EDIT_REFERENCES_DIR.exists():
        files = sorted(p for p in BEAT_EDIT_REFERENCES_DIR.iterdir() if p.suffix.lower() == ".mp4")
    else:
        files = []
    if not files:
        logger.error("No .mp4 files found in %s", BEAT_EDIT_REFERENCES_DIR)
        conn.close()
        sys.exit(1)

    results = []
    for filepath in files:
        print(f"  Processing {filepath.name} (beat-edit) ...", end=" ", flush=True)
        framework_id, status = process_beat_edit_file(filepath, cfg, vision_cfg, prompt_template, conn)
        marker = "OK" if status.startswith("OK") else "FAILED"
        print(f"→ {framework_id} [{marker}]")
        results.append((filepath.name, framework_id, status))

    conn.close()

    succeeded = sum(1 for _, _, s in results if s.startswith("OK"))
    failed    = sum(1 for _, _, s in results if s.startswith("FAILED"))
    print(f"\nSummary: {len(results)} processed | {succeeded} OK | {failed} failed")
    if failed:
        print("\nFailed:")
        for name, _, status in results:
            if status.startswith("FAILED"):
                print(f"  {name}: {status}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Instagram Reel frameworks")
    parser.add_argument("--whisper-model", default=None,
                        help="Override whisper model (tiny|base|small|medium|large)")
    parser.add_argument("--file", type=Path, default=None,
                        help="Process a single .mp4 instead of all in references/")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print assembled prompt; no LLM call, no DB writes")
    parser.add_argument("--with-vision", action="store_true",
                        help="(v1.1: disabled) Vision pass via cloud LLM")
    parser.add_argument("--beat-edit", action="store_true",
                        help="Extract beat-edit references (references/beat_edit/, vision path)")
    args = parser.parse_args()

    if args.with_vision:
        print("--with-vision is disabled in v1.1 — set [reel_extractor.vision] enabled=true in config.toml")
        sys.exit(0)

    cfg = llm_client.load_config("reel_extractor")
    if args.whisper_model:
        cfg["whisper_model"] = args.whisper_model

    single_file = args.file.resolve() if args.file else None
    if args.beat_edit:
        vision_cfg = llm_client.load_config("reel_extractor.vision")
        run_beat_edit_extraction(cfg, vision_cfg, single_file)
    else:
        run_extraction(cfg, single_file, args.dry_run)
