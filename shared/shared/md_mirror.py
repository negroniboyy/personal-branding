import re
import tomllib
from pathlib import Path
from typing import Iterable

from .logger import get_logger

logger = get_logger("md_mirror")

_REPO_ROOT = Path(__file__).parent.parent.parent  # shared/ → personal_brand/
_CONFIG_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "config.toml"


def _load_dirs() -> tuple[Path, Path]:
    try:
        with open(_CONFIG_PATH, "rb") as f:
            cfg = tomllib.load(f).get("md_mirror", {})
    except Exception:
        cfg = {}
    return (
        _REPO_ROOT / cfg.get("scripts_dir", "scripts"),
        _REPO_ROOT / cfg.get("drafts_dir", "drafts"),
    )


def _slug(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")[:40]


def _build_filename(prefix: str, item_id: int, hook_type: str, created_at: str) -> str:
    date = (created_at or "")[:10] or "0000-00-00"
    slug = _slug(str(hook_type) if hook_type else "unknown")
    return f"{date}_{prefix}-{item_id:03d}_{slug}.md"


def _build_body(meta: dict, generated_text: str) -> str:
    lines = ["---"]
    for k in ("id", "story_node_id", "framework_id", "model_used", "created_at"):
        lines.append(f"{k}: {meta.get(k, '')}")
    lines += ["---", "", generated_text or ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scripts (reel)
# ---------------------------------------------------------------------------

def write_script_md(script: dict) -> Path:
    scripts_dir, _ = _load_dirs()
    scripts_dir.mkdir(parents=True, exist_ok=True)
    filename = _build_filename(
        "reel", script["id"],
        str(script.get("framework_id", "")),
        script.get("created_at", ""),
    )
    path = scripts_dir / filename
    path.write_text(_build_body(script, script.get("generated_text", "")), encoding="utf-8")
    logger.debug("wrote script md: %s", path.name)
    return path


def delete_script_md(script_id: int) -> None:
    scripts_dir, _ = _load_dirs()
    if not scripts_dir.exists():
        return
    for p in scripts_dir.glob(f"*_reel-{script_id:03d}_*.md"):
        try:
            p.unlink()
            logger.debug("deleted script md: %s", p.name)
        except OSError as e:
            logger.warning("could not delete script md %s: %s", p, e)


def backfill_scripts(rows: Iterable[dict]) -> int:
    scripts_dir, _ = _load_dirs()
    scripts_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in rows:
        sid = row.get("id")
        if sid is None:
            continue
        if list(scripts_dir.glob(f"*_reel-{sid:03d}_*.md")):
            continue
        try:
            write_script_md(row)
            count += 1
        except Exception as e:
            logger.warning("backfill_scripts: failed for id=%s: %s", sid, e)
    if count:
        logger.info("backfilled %d script md files", count)
    return count


# ---------------------------------------------------------------------------
# Drafts (LinkedIn)
# ---------------------------------------------------------------------------

def write_draft_md(draft: dict) -> Path:
    _, drafts_dir = _load_dirs()
    drafts_dir.mkdir(parents=True, exist_ok=True)
    filename = _build_filename(
        "draft", draft["id"],
        str(draft.get("framework_id", "")),
        draft.get("created_at", ""),
    )
    path = drafts_dir / filename
    path.write_text(_build_body(draft, draft.get("generated_text", "")), encoding="utf-8")
    logger.debug("wrote draft md: %s", path.name)
    return path


def delete_draft_md(draft_id: int) -> None:
    _, drafts_dir = _load_dirs()
    if not drafts_dir.exists():
        return
    for p in drafts_dir.glob(f"*_draft-{draft_id:03d}_*.md"):
        try:
            p.unlink()
            logger.debug("deleted draft md: %s", p.name)
        except OSError as e:
            logger.warning("could not delete draft md %s: %s", p, e)


def backfill_drafts(rows: Iterable[dict]) -> int:
    _, drafts_dir = _load_dirs()
    drafts_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in rows:
        did = row.get("id")
        if did is None:
            continue
        if list(drafts_dir.glob(f"*_draft-{did:03d}_*.md")):
            continue
        try:
            write_draft_md(row)
            count += 1
        except Exception as e:
            logger.warning("backfill_drafts: failed for id=%s: %s", did, e)
    if count:
        logger.info("backfilled %d draft md files", count)
    return count
