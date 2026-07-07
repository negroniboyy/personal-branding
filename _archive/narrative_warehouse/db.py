import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

def get_db(ro: bool = False) -> sqlite3.Connection:
    uri = f"file:{DB_PATH}" + ("?mode=ro" if ro else "")
    conn = sqlite3.connect(uri, uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def run_migrations() -> None:
    conn = get_db(ro=False)
    try:
        cursor = conn.cursor()

        # 1. Add processed_status to pages if not exists
        cursor.execute("PRAGMA table_info(pages)")
        cols = {row["name"] for row in cursor.fetchall()}
        if "processed_status" not in cols:
            cursor.execute("ALTER TABLE pages ADD COLUMN processed_status INTEGER DEFAULT 0")
            conn.commit()

        # 2. Create story_nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS story_nodes (
                id              TEXT PRIMARY KEY,
                page_id         TEXT NOT NULL UNIQUE,
                created_time    TEXT NOT NULL,
                user_state      TEXT NOT NULL,
                conflict_node   TEXT NOT NULL,
                desired_outcome TEXT NOT NULL,
                the_bridge      TEXT NOT NULL,
                thematic_tags   TEXT NOT NULL,
                worth_score     REAL NOT NULL,
                narrative_flag  TEXT NOT NULL DEFAULT 'Normal',
                llm_model_used  TEXT NOT NULL,
                processed_at    TEXT NOT NULL
            )
        """)

        # 3. Create indexes for story_nodes
        for idx_name, idx_col in [
            ("idx_sn_created_time", "created_time"),
            ("idx_sn_conflict_node", "conflict_node"),
            ("idx_sn_worth_score", "worth_score"),
        ]:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON story_nodes({idx_col})")

        # 4. Create weekly_index
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_index (
                id                  TEXT PRIMARY KEY,
                week_start          TEXT NOT NULL UNIQUE,
                week_end            TEXT NOT NULL,
                total_entries       INTEGER NOT NULL,
                thread_count        INTEGER NOT NULL,
                open_loops          INTEGER NOT NULL,
                closed_loops        INTEGER NOT NULL,
                sentiment_delta     REAL NOT NULL,
                thread_summary_json TEXT NOT NULL,
                generated_at        TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wi_week_start ON weekly_index(week_start)")

        # 5. Create threads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id               TEXT PRIMARY KEY,
                conflict_node    TEXT NOT NULL UNIQUE,
                display_name     TEXT NOT NULL,
                first_seen       TEXT NOT NULL,
                last_seen        TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL,
                current_status   TEXT NOT NULL DEFAULT 'Open',
                closed_week_start TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_t_conflict ON threads(conflict_node)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_t_status ON threads(current_status)")

        conn.commit()
    finally:
        conn.close()