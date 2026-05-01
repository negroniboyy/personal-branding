#!/usr/bin/env python3
"""Ingest a live Google Sheet snapshot into the SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

CONTENT_SHEET = "Content List"
ARC_SHEET = "Content Live"


def normalize(value) -> str:
    return str(value).strip() if value is not None else ""


def sheet_as_dicts(rows: list[list[object]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [normalize(value) for value in rows[0]]
    dict_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows[1:], start=2):
        values = {
            headers[col]: normalize(row[col])
            for col in range(min(len(headers), len(row)))
            if headers[col]
        }
        if any(values.values()):
            values["_row"] = str(idx)
            dict_rows.append(values)
    return dict_rows


def normalize_row_dicts(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=2):
        values = {normalize(key): normalize(value) for key, value in row.items() if normalize(key)}
        if any(value for key, value in values.items() if key != "_row"):
            values.setdefault("_row", str(idx))
            normalized_rows.append(values)
    return normalized_rows


def extract_rows(payload: dict[str, object], sheet_name: str, direct_key: str) -> list[dict[str, str]]:
    direct = payload.get(direct_key)
    if isinstance(direct, list) and direct:
        first = direct[0]
        if isinstance(first, dict):
            return normalize_row_dicts(direct)
        if isinstance(first, list):
            return sheet_as_dicts(direct)

    tabs = payload.get("tabs")
    if isinstance(tabs, dict):
        tab_payload = tabs.get(sheet_name)
        if isinstance(tab_payload, dict):
            rows = tab_payload.get("rows")
            if isinstance(rows, list) and rows:
                first = rows[0]
                if isinstance(first, dict):
                    return normalize_row_dicts(rows)
                if isinstance(first, list):
                    return sheet_as_dicts(rows)
            values = tab_payload.get("values")
            if isinstance(values, list):
                return sheet_as_dicts(values)
    return []


def load_snapshot(snapshot_path: Path) -> tuple[dict[str, object], list[dict[str, str]], list[dict[str, str]]]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Snapshot payload must be a JSON object")
    content_rows = extract_rows(payload, CONTENT_SHEET, "content_rows")
    arc_rows = extract_rows(payload, ARC_SHEET, "month_arc_rows")
    if not content_rows:
        raise ValueError(f"Snapshot is missing rows for {CONTENT_SHEET}")
    return payload, content_rows, arc_rows


def queue_identifier(values: dict[str, str], sheet_name: str, row_idx: int) -> str:
    return values.get("ID") or values.get("Proposal ID") or f"{sheet_name}:{row_idx}"


def source_system(payload: dict[str, object]) -> str:
    source = payload.get("source")
    if isinstance(source, dict):
        return normalize(source.get("type")) or "google_sheet"
    return "google_sheet"


def upsert_content_item(conn: sqlite3.Connection, source: str, sheet_name: str, row_idx: int, values: dict[str, str]) -> None:
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
            source,
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


def upsert_planner_slot(conn: sqlite3.Connection, source: str, sheet_name: str, row_idx: int, values: dict[str, str]) -> None:
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
            source,
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


def record_sync(conn: sqlite3.Connection, source: str, action: str, details: dict) -> None:
    conn.execute(
        """
        INSERT INTO sync_runs (source, action, status, finished_at, details_json)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        """,
        (source, action, "success", json.dumps(details, ensure_ascii=False)),
    )


def ingest(db_path: Path, snapshot_path: Path) -> dict[str, int]:
    payload, content_rows, arc_rows = load_snapshot(snapshot_path)
    source = source_system(payload)
    conn = sqlite3.connect(db_path)
    ingested_content = 0
    ingested_slots = 0
    try:
        for values in content_rows:
            row_idx = int(normalize(values.get("_row")) or "0")
            if not any(value for key, value in values.items() if key != "_row"):
                continue
            upsert_content_item(conn, source, CONTENT_SHEET, row_idx, values)
            ingested_content += 1

        for values in arc_rows:
            row_idx = int(normalize(values.get("_row")) or "0")
            if not any(value for key, value in values.items() if key != "_row"):
                continue
            upsert_planner_slot(conn, source, ARC_SHEET, row_idx, values)
            ingested_slots += 1

        source_meta = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        record_sync(
            conn,
            source,
            "ingest_content_snapshot",
            {
                "snapshot": str(snapshot_path),
                "spreadsheet_id": normalize(source_meta.get("spreadsheet_id")),
                "spreadsheet_url": normalize(source_meta.get("spreadsheet_url")),
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
    parser.add_argument("--snapshot", required=True, help="Path to a live Google Sheet snapshot JSON file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats = ingest(Path(args.db).expanduser().resolve(), Path(args.snapshot).expanduser().resolve())
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
