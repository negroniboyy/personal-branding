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


def _make_story_node_nullable(conn: sqlite3.Connection) -> None:
    info = conn.execute("PRAGMA table_info(content_drafts)").fetchall()
    col = next((r for r in info if r["name"] == "story_node_id"), None)
    if col is None or col["notnull"] == 0:
        return
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS content_drafts_new (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            story_node_id  INTEGER,
            framework_id   INTEGER NOT NULL,
            idea_prompt    TEXT,
            generated_text TEXT NOT NULL,
            model_used     TEXT NOT NULL,
            created_at     DATETIME DEFAULT (datetime('now')),
            idea_id        TEXT REFERENCES ideas(id)
        );
        INSERT INTO content_drafts_new
            SELECT id, story_node_id, framework_id, idea_prompt,
                   generated_text, model_used, created_at,
                   CASE WHEN EXISTS(SELECT 1 FROM pragma_table_info('content_drafts') WHERE name='idea_id')
                        THEN idea_id ELSE NULL END
            FROM content_drafts;
        DROP TABLE content_drafts;
        ALTER TABLE content_drafts_new RENAME TO content_drafts;
    """)
    conn.commit()


def run_migration(conn: sqlite3.Connection) -> None:
    from shared.lifecycle import migrate_lifecycle_columns

    conn.executescript(_MIGRATION)
    for alter in [
        "ALTER TABLE content_drafts ADD COLUMN idea_id TEXT REFERENCES ideas(id)",
        "ALTER TABLE frameworks ADD COLUMN description TEXT DEFAULT ''",
        "ALTER TABLE content_drafts ADD COLUMN cost_usd REAL DEFAULT 0.0",
    ]:
        try:
            conn.execute(alter)
        except Exception:
            pass
    conn.commit()
    _make_story_node_nullable(conn)
    migrate_lifecycle_columns(conn, "content_drafts")
    _backfill_framework_descriptions(conn)
