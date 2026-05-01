#!/usr/bin/env python3
"""Ingest the fallback local CONTENT.xlsx workbook into the SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

def resolve_repo_root() -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / "py" / "content_workbook.py").exists():
            return candidate
    raise RuntimeError("Could not locate repo root with py/content_workbook.py")


ROOT = resolve_repo_root()
sys.path.insert(0, str(ROOT / "py"))

from content_workbook import read_sheet_rows, sheet_rows_as_dicts  # noqa: E402


TRACKED_SHEETS = ("Content List", "Sheet1", "v2")
PLANNER_SHEETS = ("Content Live",)


def normalize(value) -> str:
    return str(value).strip() if value is not None else ""


def queue_identifier(values: dict[str, str], sheet_name: str, row_idx: int) -> str:
    return values.get("ID") or values.get("Proposal ID") or f"{sheet_name}:{row_idx}"


def upsert_content_item(conn: sqlite3.Connection, sheet_name: str, row_idx: int, values: dict[str, str]) -> None:
    conn.execute(
        """
        INSERT INTO content_items (
            source_system, source_tab, source_row, channel, title, brief, category,
            review_decision, production_status, proposal_id, planner_source,
            draft_due, review_due, scheduled_date, draft_doc, publish_status,
            published_date, published_url, manager_notes, linkedin_post_urn,
            linkedin_author_urn, updated_at, last_ingested_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT(source_system, source_tab, source_row) DO UPDATE SET
            channel = excluded.channel,
            title = excluded.title,
            brief = excluded.brief,
            category = excluded.category,
            review_decision = excluded.review_decision,
            production_status = excluded.production_status,
            proposal_id = excluded.proposal_id,
            planner_source = excluded.planner_source,
            draft_due = excluded.draft_due,
            review_due = excluded.review_due,
            scheduled_date = excluded.scheduled_date,
            draft_doc = excluded.draft_doc,
            publish_status = excluded.publish_status,
            published_date = excluded.published_date,
            published_url = excluded.published_url,
            manager_notes = excluded.manager_notes,
            linkedin_post_urn = excluded.linkedin_post_urn,
            linkedin_author_urn = excluded.linkedin_author_urn,
            updated_at = CURRENT_TIMESTAMP,
            last_ingested_at = CURRENT_TIMESTAMP
        """,
        (
            "local_workbook",
            sheet_name,
            row_idx,
            values.get("Channel", ""),
            values.get("Title", ""),
            values.get("Content", ""),
            values.get("Category", ""),
            values.get("Review decision", ""),
            values.get("Production status", ""),
            queue_identifier(values, sheet_name, row_idx),
            values.get("Planner Source", ""),
            values.get("Draft due", ""),
            values.get("Review due", ""),
            values.get("Scheduled date", ""),
            values.get("Draft doc", ""),
            values.get("Publish status", ""),
            values.get("Published date", ""),
            values.get("Published URL", ""),
            values.get("Manager notes", ""),
            values.get("LinkedIn Post URN", ""),
            values.get("LinkedIn Author URN", ""),
        ),
    )


def upsert_planner_slot(conn: sqlite3.Connection, sheet_name: str, row_idx: int, values: dict[str, str]) -> None:
    conn.execute(
        """
        INSERT INTO planner_slots (
            source_system, source_tab, source_row, slot_label, title, angle, narrative_spine,
            source_fit, core_tension, opening_scene, notes, draft_due, review_due,
            scheduled_date, production_status, updated_at, last_ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(source_system, source_tab, source_row) DO UPDATE SET
            slot_label = excluded.slot_label,
            title = excluded.title,
            angle = excluded.angle,
            narrative_spine = excluded.narrative_spine,
            source_fit = excluded.source_fit,
            core_tension = excluded.core_tension,
            opening_scene = excluded.opening_scene,
            notes = excluded.notes,
            draft_due = excluded.draft_due,
            review_due = excluded.review_due,
            scheduled_date = excluded.scheduled_date,
            production_status = excluded.production_status,
            updated_at = CURRENT_TIMESTAMP,
            last_ingested_at = CURRENT_TIMESTAMP
        """,
        (
            "local_workbook",
            sheet_name,
            row_idx,
            values.get("When to post", ""),
            values.get("Title", ""),
            values.get("Angle", ""),
            values.get("Narrative spine", ""),
            values.get("Source fit", ""),
            values.get("Core tension", ""),
            values.get("Opening scene", ""),
            values.get("Notes", ""),
            values.get("Draft due", ""),
            values.get("Review due", ""),
            values.get("Scheduled date", ""),
            values.get("Production status", ""),
        ),
    )


def record_sync(conn: sqlite3.Connection, action: str, details: dict) -> None:
    conn.execute(
        """
        INSERT INTO sync_runs (source, action, status, finished_at, details_json)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        """,
        ("local_workbook", action, "success", json.dumps(details, ensure_ascii=False)),
    )


def ingest(db_path: Path, workbook_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    ingested_content = 0
    ingested_slots = 0
    try:
        for sheet_name in TRACKED_SHEETS:
            try:
                rows = sheet_rows_as_dicts(read_sheet_rows(workbook_path, sheet_name))
            except ValueError:
                continue
            for values in rows:
                row_idx = int(normalize(values.get("_row")) or "0")
                if not any(value for key, value in values.items() if key != "_row"):
                    continue
                upsert_content_item(conn, sheet_name, row_idx, values)
                ingested_content += 1

        for sheet_name in PLANNER_SHEETS:
            try:
                rows = sheet_rows_as_dicts(read_sheet_rows(workbook_path, sheet_name))
            except ValueError:
                continue
            for values in rows:
                row_idx = int(normalize(values.get("_row")) or "0")
                if not any(value for key, value in values.items() if key != "_row"):
                    continue
                upsert_planner_slot(conn, sheet_name, row_idx, values)
                ingested_slots += 1

        record_sync(
            conn,
            "ingest_content_workbook",
            {
                "workbook": str(workbook_path),
                "content_rows": ingested_content,
                "planner_rows": ingested_slots,
            },
        )
        conn.commit()
    finally:
        conn.close()
    return {"content_rows": ingested_content, "planner_rows": ingested_slots}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Path to the SQLite database file")
    parser.add_argument("--workbook", required=True, help="Path to fallback CONTENT.xlsx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats = ingest(Path(args.db).expanduser().resolve(), Path(args.workbook).expanduser().resolve())
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
