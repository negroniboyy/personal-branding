import sqlite3
import tomllib
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


def run_migration(conn: sqlite3.Connection) -> None:
    conn.executescript(_MIGRATION)
    conn.commit()
