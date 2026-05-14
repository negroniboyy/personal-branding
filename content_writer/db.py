import sqlite3
import tomllib
import yaml
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "config.toml"
_DEFAULT_DB = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

_MIGRATION = """
CREATE TABLE IF NOT EXISTS content_drafts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    story_node_id  INTEGER NOT NULL,
    framework_id   INTEGER NOT NULL,
    idea_prompt    TEXT,
    generated_text TEXT NOT NULL,
    model_used     TEXT NOT NULL,
    created_at     DATETIME DEFAULT (datetime('now'))
);
"""


def get_db_path() -> str:
    try:
        with open(_CONFIG_PATH, "rb") as f:
            cfg = tomllib.load(f)
        return cfg.get("content_writer", {}).get("db_path", str(_DEFAULT_DB))
    except FileNotFoundError:
        return str(_DEFAULT_DB)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _backfill_framework_descriptions(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, yaml_path FROM frameworks WHERE description IS NULL OR description = ''"
    ).fetchall()
    for row in rows:
        try:
            with open(row["yaml_path"], "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            desc = (data or {}).get("description", "")
            if desc:
                conn.execute("UPDATE frameworks SET description = ? WHERE id = ?", (desc, row["id"]))
        except Exception:
            pass
    conn.commit()


def run_migration(conn: sqlite3.Connection) -> None:
    conn.executescript(_MIGRATION)
    for alter in [
        "ALTER TABLE content_drafts ADD COLUMN idea_id TEXT REFERENCES ideas(id)",
        "ALTER TABLE frameworks ADD COLUMN description TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(alter)
        except Exception:
            pass
    conn.commit()
    _backfill_framework_descriptions(conn)
