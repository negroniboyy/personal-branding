"""Framework management API — list, view, edit, delete frameworks from both channels."""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.logger import get_logger

logger = get_logger("frameworks_api")

_REPO_ROOT = Path(__file__).parent.parent
_DB_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

router = APIRouter(prefix="/frameworks", tags=["frameworks"])


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PutFrameworkBody(BaseModel):
    yaml_text: str


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _row_to_item(row: sqlite3.Row, channel: str) -> dict:
    d = dict(row)
    d["channel"] = channel
    d["uid"] = f"{channel}-{d['id']}"
    return d


def _get_stats(conn: sqlite3.Connection, table: str, fw_id: str) -> dict:
    row = conn.execute(
        f"SELECT COUNT(*) AS used, "
        f"SUM(CASE WHEN status IN ('approved', 'recorded', 'posted') THEN 1 ELSE 0 END) AS approved, "
        f"SUM(CASE WHEN status = 'killed' THEN 1 ELSE 0 END) AS killed "
        f"FROM {table} WHERE framework_id = ?",
        (fw_id,),
    ).fetchone()
    return {
        "used": row["used"] or 0,
        "approved": row["approved"] or 0,
        "killed": row["killed"] or 0,
    }


def _get_linkedin(conn: sqlite3.Connection, fw_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM frameworks WHERE id = ?", (fw_id,)).fetchone()
    if not row:
        return None
    item = _row_to_item(row, "linkedin")
    item.update(_get_stats(conn, "content_drafts", fw_id))
    return item


def _get_reel(conn: sqlite3.Connection, fw_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM reel_frameworks WHERE id = ?", (fw_id,)).fetchone()
    if not row:
        return None
    item = _row_to_item(row, "reels")
    item.update(_get_stats(conn, "reel_scripts", fw_id))
    return item


def _update_linkedin(conn: sqlite3.Connection, fw_id: str, data: dict) -> None:
    hook = data.get("hook", {}) or {}
    cta = data.get("cta", {}) or {}

    def _j(v):
        return json.dumps(v) if isinstance(v, (list, dict)) else (str(v) if v is not None else "")

    conn.execute("""
        UPDATE frameworks SET
            hook_type = ?, hook_first_line = ?, structure_json = ?,
            paragraph_style = ?, tone = ?, cta_type = ?,
            fits_topics = ?, description = ?
        WHERE id = ?
    """, (
        str(hook.get("type", "") or ""),
        str(hook.get("first_line", "") or ""),
        _j(data.get("structure", [])),
        str(data.get("paragraph_style", "") or ""),
        str(data.get("tone", "") or ""),
        str(cta.get("type", "") or ""),
        _j(data.get("fits_topics", [])),
        str(data.get("description", "") or ""),
        fw_id,
    ))
    conn.commit()


def _update_reel(conn: sqlite3.Connection, fw_id: str, data: dict) -> None:
    hook = data.get("hook", {}) or {}
    cta = data.get("cta", {}) or {}

    def _j(v):
        return json.dumps(v) if isinstance(v, (list, dict)) else (str(v) if v is not None else "")

    conn.execute("""
        UPDATE reel_frameworks SET
            hook_type = ?, hook_verbal = ?, structure_json = ?,
            pacing = ?, tone = ?, cta_type = ?, cta_verbal = ?,
            fits_topics = ?, description = ?
        WHERE id = ?
    """, (
        str(hook.get("type", "") or ""),
        str(hook.get("verbal", "") or ""),
        _j(data.get("structure", [])),
        str(data.get("pacing", "") or ""),
        str(data.get("tone", "") or ""),
        str(cta.get("type", "") or ""),
        str(cta.get("verbal", "") or ""),
        _j(data.get("fits_topics", [])),
        str(data.get("description", "") or ""),
        fw_id,
    ))
    conn.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

_STATS_SUBQUERY = """
    SELECT framework_id,
           COUNT(*) AS used,
           SUM(CASE WHEN status IN ('approved', 'recorded', 'posted') THEN 1 ELSE 0 END) AS approved,
           SUM(CASE WHEN status = 'killed' THEN 1 ELSE 0 END) AS killed
    FROM {table}
    GROUP BY framework_id
"""


@router.get("")
def list_frameworks():
    conn = _db()
    try:
        linkedin = [_row_to_item(r, "linkedin") for r in conn.execute(
            "SELECT f.id, f.hook_type, f.tone, f.cta_type, f.description, f.source_file, f.yaml_path, "
            "COALESCE(s.used, 0) AS used, COALESCE(s.approved, 0) AS approved, COALESCE(s.killed, 0) AS killed "
            "FROM frameworks f LEFT JOIN (" + _STATS_SUBQUERY.format(table="content_drafts") + ") s "
            "ON s.framework_id = f.id ORDER BY f.id"
        ).fetchall()]
        reels = [_row_to_item(r, "reels") for r in conn.execute(
            "SELECT f.id, f.hook_type, f.tone, f.cta_type, f.pacing, f.description, f.source_file, f.yaml_path, "
            "COALESCE(s.used, 0) AS used, COALESCE(s.approved, 0) AS approved, COALESCE(s.killed, 0) AS killed "
            "FROM reel_frameworks f LEFT JOIN (" + _STATS_SUBQUERY.format(table="reel_scripts") + ") s "
            "ON s.framework_id = f.id ORDER BY f.id"
        ).fetchall()]
        return {"linkedin": linkedin, "reels": reels}
    finally:
        conn.close()


@router.get("/{channel}/{fw_id:path}")
def get_framework(channel: str, fw_id: str):
    if channel not in ("linkedin", "reels"):
        raise HTTPException(status_code=400, detail="channel must be 'linkedin' or 'reels'")
    conn = _db()
    try:
        item = _get_linkedin(conn, fw_id) if channel == "linkedin" else _get_reel(conn, fw_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Framework {fw_id} not found")
        yaml_path = Path(item.get("yaml_path", ""))
        yaml_text = yaml_path.read_text(encoding="utf-8") if yaml_path.exists() else ""
        return {**item, "yaml_text": yaml_text}
    finally:
        conn.close()


@router.put("/{channel}/{fw_id:path}")
def put_framework(channel: str, fw_id: str, body: PutFrameworkBody):
    if channel not in ("linkedin", "reels"):
        raise HTTPException(status_code=400, detail="channel must be 'linkedin' or 'reels'")
    try:
        parsed = yaml.safe_load(body.yaml_text)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="YAML must be a mapping")

    conn = _db()
    try:
        item = _get_linkedin(conn, fw_id) if channel == "linkedin" else _get_reel(conn, fw_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Framework {fw_id} not found")
        yaml_path = Path(item["yaml_path"])
        yaml_path.write_text(body.yaml_text, encoding="utf-8")
        if channel == "linkedin":
            _update_linkedin(conn, fw_id, parsed)
        else:
            _update_reel(conn, fw_id, parsed)
        logger.info("updated framework %s/%s", channel, fw_id)
        updated = _get_linkedin(conn, fw_id) if channel == "linkedin" else _get_reel(conn, fw_id)
        return {**updated, "yaml_text": body.yaml_text}
    finally:
        conn.close()


@router.delete("/{channel}/{fw_id:path}")
def delete_framework(channel: str, fw_id: str):
    if channel not in ("linkedin", "reels"):
        raise HTTPException(status_code=400, detail="channel must be 'linkedin' or 'reels'")
    conn = _db()
    try:
        item = _get_linkedin(conn, fw_id) if channel == "linkedin" else _get_reel(conn, fw_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Framework {fw_id} not found")
        yaml_path = Path(item.get("yaml_path", ""))
        try:
            if yaml_path.exists():
                yaml_path.unlink()
        except OSError as e:
            logger.warning("could not delete yaml file %s: %s", yaml_path, e)
        table = "frameworks" if channel == "linkedin" else "reel_frameworks"
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (fw_id,))
        conn.commit()
        logger.info("deleted framework %s/%s", channel, fw_id)
        return {"ok": True}
    finally:
        conn.close()
