#!/usr/bin/env python3
"""
Extract LinkedIn post frameworks from .txt reference files.
Outputs YAML files and inserts records into the frameworks SQLite table.
"""

import argparse
import json
import re
import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml

from llm_client import complete, set_prompt_template_path, inject_post_text
from shared.logger import get_logger

logger = get_logger("linkedin_frameworks")

# Resolve paths relative to this script's location
SCRIPT_DIR = Path(__file__).parent.resolve()
REFERENCES_DIR = SCRIPT_DIR / "references"
PROMPTS_DIR = SCRIPT_DIR / "prompts"
FRAMEWORKS_DIR = SCRIPT_DIR / "frameworks"
PROMPT_TEMPLATE_PATH = PROMPTS_DIR / "extract_linkedin.txt"
DB_PATH = Path(__file__).parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"
# Handle case where NOTION DIARY FETCHER is a sibling of frameworks
if not DB_PATH.exists():
    DB_PATH = Path(__file__).parent.parent.parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

REQUIRED_FIELDS = [
    "creator", "channel", "source_file",
    "hook", "structure", "paragraph_style",
    "whitespace_use", "tone", "cta", "fits_topics", "raw_excerpt",
]
CTA_TYPES = {"question", "soft_sell", "save_this", "follow", "none"}
HOOK_TYPES = {"bold_claim", "question", "story_open", "stat", "pain_point", "contrarian"}
MIN_FILE_SIZE = 50


def init_db():
    """Create frameworks table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS frameworks (
            id              TEXT PRIMARY KEY,
            creator         TEXT NOT NULL,
            channel         TEXT NOT NULL DEFAULT 'linkedin',
            source_file     TEXT NOT NULL,
            hook_type       TEXT NOT NULL,
            hook_first_line TEXT,
            structure_json  TEXT NOT NULL,
            paragraph_style TEXT NOT NULL,
            whitespace_use  TEXT NOT NULL,
            tone            TEXT NOT NULL,
            cta_type        TEXT NOT NULL,
            cta_example     TEXT,
            fits_topics     TEXT NOT NULL,
            performance_notes TEXT,
            raw_excerpt     TEXT NOT NULL,
            yaml_path       TEXT NOT NULL,
            created_at      TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fw_creator ON frameworks(creator)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fw_hook_type ON frameworks(hook_type)")
    conn.commit()
    conn.close()


def validate(data: dict) -> list[str]:
    """Return list of missing or empty required fields."""
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None or data[field] == "":
            missing.append(field)
    # Validate nested fields
    if "hook" in data:
        if not isinstance(data["hook"], dict):
            missing.append("hook (not a dict)")
        else:
            if "type" not in data["hook"] or not data["hook"]["type"]:
                missing.append("hook.type")
            if "first_line" not in data["hook"] or not data["hook"]["first_line"]:
                missing.append("hook.first_line")
    if "cta" in data:
        if not isinstance(data["cta"], dict):
            missing.append("cta (not a dict)")
        else:
            if "type" not in data["cta"] or data["cta"]["type"] not in CTA_TYPES:
                missing.append("cta.type")
    if "fits_topics" in data:
        if not isinstance(data["fits_topics"], list) or len(data["fits_topics"]) < 1:
            missing.append("fits_topics (must be non-empty list)")
    if "structure" in data:
        if not isinstance(data["structure"], list) or len(data["structure"]) < 1:
            missing.append("structure (must be non-empty list)")
    return missing


_PRE_EXTRACT_PATTERN = re.compile(
    r'^(hook\.type|hook\.first_line|cta\.type|cta\.example|fits_topics)\s*:[ \t]*(.*)',
    re.MULTILINE,
)


def parse_yaml_with_fallback(raw: str) -> dict | None:
    """Parse LLM YAML output with pre-extraction of fields that commonly break parsing.

    Problems handled:
    - hook.first_line / cta.example values with ': ' inside (colon-space breaks YAML)
    - fits_topics as quoted comma-separated or space-separated strings (invalid block syntax)
    - raw_excerpt as block scalar (|) or plain multi-line value with trailing content
    - Multi-document YAML / markdown fences
    """
    text = raw.strip()
    if not text:
        return None

    # Handle two docs merged without --- separator
    if "\nframework_id:" in text:
        text = text.split("\nframework_id:")[0]

    # Strip markdown fences
    text = text.lstrip("```yaml").lstrip("```").strip()
    text = text.removesuffix("```").strip()

    # Pre-extract raw_excerpt — always causes issues with trailing multi-line content
    raw_excerpt_value = None
    if "\nraw_excerpt:" in text:
        idx = text.find("\nraw_excerpt:")
        after_key = text[idx + len("\nraw_excerpt:"):]
        stripped_after = after_key.lstrip(" \t")
        if stripped_after.startswith(("|", ">")):
            # Block scalar: pull first non-empty line after the indicator.
            # Content may be indented (proper YAML) or not (model error) — accept either.
            raw_excerpt_value = ""
            for line in after_key.split("\n")[1:]:
                stripped = line.strip()
                if stripped:
                    raw_excerpt_value = stripped.lstrip("- ").strip()
                    break
        else:
            raw_excerpt_value = after_key.split("\n")[0].strip()
        text = text[:idx].rstrip()

    # Pre-extract flat dotted fields whose values break YAML
    # (colons in free-text values, quoted CSV strings, etc.)
    # Only capture when there IS an inline value — empty means a block follows
    # (e.g. fits_topics: followed by a block sequence) which YAML handles fine.
    pre_extracted: dict[str, str] = {}

    def _capture(m: re.Match) -> str:
        value = m.group(2).strip()
        if value:
            pre_extracted[m.group(1)] = value
            return ""  # remove the line — we'll re-inject after parsing
        return m.group(0)  # leave empty-value line for YAML block parsing

    text = _PRE_EXTRACT_PATTERN.sub(_capture, text)

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    # Re-inject pre-extracted fields as raw strings (normalization runs later).
    # Don't overwrite fields the YAML parser already resolved to a proper type
    # (e.g. fits_topics resolved as a list from a block sequence).
    for key, value in pre_extracted.items():
        if key not in data or data[key] is None:
            data[key] = value

    if raw_excerpt_value is not None:
        data["raw_excerpt"] = raw_excerpt_value

    return data


def normalize_fits_topics(data: dict) -> None:
    """Convert string fits_topics to a list, handling all LLM output variants."""
    if "fits_topics" in data and isinstance(data["fits_topics"], str):
        val = data["fits_topics"].strip().strip("[]")
        if "," in val:
            topics = [t.strip().strip('"').strip("'") for t in val.split(",")]
        else:
            # Space-separated quoted strings: "a" "b" "c"
            tokens = re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', val)
            topics = [t[0] or t[1] or t[2] for t in tokens]
        data["fits_topics"] = [t for t in topics if t]


def normalize_source_file(data: dict, fallback: str) -> None:
    """Ensure source_file is a non-empty string."""
    sf = data.get("source_file", "")
    if isinstance(sf, list):
        sf = sf[0] if sf else ""
    sf = str(sf).strip() if sf else ""
    if not sf or sf in ("null", "None", "unknown", "[original filename not provided]", "N/A"):
        data["source_file"] = fallback
    else:
        data["source_file"] = sf


def _unquote(value: str | None) -> str | None:
    """Strip surrounding YAML double or single quotes from a pre-extracted string."""
    if not value:
        return value
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


def normalize_nested_fields(data: dict) -> None:
    """Convert flat hook.type / hook.first_line / cta.type / cta.example
    into nested hook: {type, first_line} and cta: {type, example} dicts."""
    # hook
    hook_type = _unquote(data.pop("hook.type", None))
    hook_first_line = _unquote(data.pop("hook.first_line", None))
    existing_hook = data.get("hook")
    if isinstance(existing_hook, dict):
        if hook_type and "type" not in existing_hook:
            existing_hook["type"] = hook_type
        if hook_first_line and "first_line" not in existing_hook:
            existing_hook["first_line"] = hook_first_line
    elif hook_type or hook_first_line:
        data["hook"] = {"type": hook_type or "", "first_line": hook_first_line or ""}
    # cta
    cta_type = _unquote(data.pop("cta.type", None))
    cta_example = _unquote(data.pop("cta.example", None))
    existing_cta = data.get("cta")
    if isinstance(existing_cta, dict):
        if cta_type and "type" not in existing_cta:
            existing_cta["type"] = cta_type
        if cta_example and "example" not in existing_cta:
            existing_cta["example"] = cta_example
    elif cta_type or cta_example:
        data["cta"] = {"type": cta_type or "", "example": cta_example or ""}


def generate_framework_id(source_file: str, hook_type: str) -> str:
    """Generate a framework ID from source filename and hook type."""
    name = Path(source_file).stem
    safe_name = name.lower().replace(" ", "-")
    return f"{safe_name}-linkedin-{hook_type}-v1"


def save_yaml(framework_id: str, data: dict) -> Path:
    """Save framework data as a YAML file."""
    FRAMEWORKS_DIR.mkdir(parents=True, exist_ok=True)
    path = FRAMEWORKS_DIR / f"{framework_id}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path


def insert_db_row(framework_id: str, data: dict, yaml_path: Path) -> bool:
    """Insert a framework record into the SQLite database. Returns True on success."""
    conn = sqlite3.connect(DB_PATH)
    try:
        now = datetime.now(timezone.utc).isoformat()
        hook = data.get("hook", {})
        cta = data.get("cta", {})
        structure_json = json.dumps(data.get("structure", []))
        fits_topics_json = json.dumps(data.get("fits_topics", []))
        def _s(v) -> str:
            """Coerce any scalar to a string safe for SQLite binding."""
            if v is None:
                return ""
            if isinstance(v, (list, dict)):
                return json.dumps(v)
            return str(v)

        conn.execute("""
            INSERT OR REPLACE INTO frameworks (
                id, creator, channel, source_file,
                hook_type, hook_first_line,
                structure_json, paragraph_style,
                whitespace_use, tone,
                cta_type, cta_example,
                fits_topics,
                performance_notes,
                raw_excerpt, yaml_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            framework_id,
            _s(data.get("creator", "unknown")),
            _s(data.get("channel", "linkedin")),
            _s(data.get("source_file", "")),
            _s(hook.get("type", "")),
            _s(hook.get("first_line", "")),
            structure_json,
            _s(data.get("paragraph_style", "")),
            _s(data.get("whitespace_use", "")),
            _s(data.get("tone", "")),
            _s(cta.get("type", "")),
            _s(cta.get("example", "")),
            fits_topics_json,
            _s(data.get("performance_notes", "")),
            _s(data.get("raw_excerpt", "")),
            str(yaml_path),
            now,
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.warning("DB insert failed for %s: %s", framework_id, e)
        return False
    finally:
        conn.close()


def process_file(filepath: Path, prompt_template: str) -> tuple[str, str]:
    """
    Process a single .txt file. Returns (framework_id, status).
    status is "OK", "FAILED: reason", or "SKIPPED: reason".
    """
    if filepath.stat().st_size < MIN_FILE_SIZE:
        return filepath.name, f"SKIPPED: file too small ({filepath.stat().st_size} bytes)"

    post_text = filepath.read_text(encoding="utf-8").strip()
    if len(post_text) < MIN_FILE_SIZE:
        return filepath.name, f"SKIPPED: content too small ({len(post_text)} chars)"

    prompt = inject_post_text(prompt_template, post_text)
    raw_response = complete(prompt, tier="local", dry_run=False)

    data = parse_yaml_with_fallback(raw_response)
    if data is None:
        # Save raw response for manual inspection
        failed_dir = FRAMEWORKS_DIR / "failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        failed_path = failed_dir / f"{filepath.stem}.raw.txt"
        failed_path.write_text(raw_response, encoding="utf-8")
        return filepath.name, "FAILED: unparseable YAML"

    normalize_fits_topics(data)
    normalize_source_file(data, filepath.name)
    normalize_nested_fields(data)

    missing = validate(data)
    if missing:
        return filepath.name, f"FAILED: missing fields: {', '.join(missing)}"

    source_file = filepath.name
    hook_type = (data.get("hook", {}) or {}).get("type", "unknown")
    framework_id = generate_framework_id(source_file, hook_type)

    yaml_path = save_yaml(framework_id, data)
    db_ok = insert_db_row(framework_id, data, yaml_path)

    if db_ok:
        return framework_id, "OK"
    else:
        return framework_id, "OK (DB insert warning)"


def run_extraction(dry_run: bool):
    set_prompt_template_path(str(PROMPT_TEMPLATE_PATH))
    prompt_template = open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8").read()
    init_db()

    txt_files = sorted(REFERENCES_DIR.glob("*.txt"))
    if not txt_files:
        logger.error("No .txt files found in %s", REFERENCES_DIR)
        sys.exit(1)

    results = []
    for filepath in txt_files:
        framework_id, status = process_file(filepath, prompt_template)
        marker = "OK" if status.startswith("OK") else "FAILED"
        print(f"  {filepath.name} → {framework_id} [{marker}]")
        results.append((filepath.name, framework_id, status))

    succeeded = sum(1 for _, _, s in results if s.startswith("OK"))
    failed = sum(1 for _, _, s in results if s.startswith("FAILED"))
    skipped = sum(1 for _, _, s in results if s.startswith("SKIPPED"))

    print()
    print(f"Summary: {len(results)} processed | {succeeded} OK | {failed} failed | {skipped} skipped")
    if failed:
        print()
        print("Failed files:")
        for name, _, status in results:
            if status.startswith("FAILED"):
                print(f"  {name}: {status}")
    if skipped:
        print()
        print("Skipped files:")
        for name, _, status in results:
            if status.startswith("SKIPPED"):
                print(f"  {name}: {status}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract LinkedIn content frameworks")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without calling LLM")
    args = parser.parse_args()

    if args.dry_run:
        # Just load the template and print it with a sample injection
        prompt_template = open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8").read()
        sample = "[Sample LinkedIn post would appear here — this is a dry run]"
        print(inject_post_text(prompt_template, sample))
        sys.exit(0)

    run_extraction(dry_run=False)