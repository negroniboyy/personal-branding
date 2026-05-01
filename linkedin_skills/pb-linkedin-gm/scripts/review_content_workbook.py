#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path


X_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
R_NS = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
PKG_REL_NS = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
CONTENT_SHEET = "Content List"
ARC_SHEET = "Content Live"
DUE_COLUMNS = ("Draft due", "Review due", "Scheduled date")
REQUIRED_REVIEW_FIELDS = (
    "Title",
    "Content",
    "Category",
    "Channel",
    "Planner Source",
    "Production status",
)


def normalize(value) -> str:
    return str(value).strip() if value is not None else ""


def canonical_review_decision(raw: str) -> str:
    value = normalize(raw).lower()
    if value == "approved":
        return "Approved"
    if value == "disapproved":
        return "Disapproved"
    if value == "manual":
        return "MANUAL"
    return ""


def canonical_production_status(row: dict[str, str]) -> str:
    raw = normalize(row.get("Production status")).lower()
    if raw == "backlog":
        return "Backlog"
    if raw == "drafting":
        return "Drafting"
    if raw == "ready":
        return "Ready"
    if raw == "done":
        return "Done"

    publish_status = normalize(row.get("Publish status")).lower()
    if normalize(row.get("Published date")) or normalize(row.get("Published URL")) or "published" in publish_status:
        return "Done"
    if normalize(row.get("Draft doc")) or normalize(row.get("Scheduled date")) or "scheduled" in publish_status:
        return "Ready"
    return "Backlog"


def parse_date(raw: str) -> date | None:
    value = normalize(raw)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def is_in_window(candidate: date | None, start: date, end: date) -> bool:
    return candidate is not None and start <= candidate <= end


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(".//x:si", X_NS):
        values.append("".join(item.itertext()).strip())
    return values


def workbook_sheet_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(".//pr:Relationship", PKG_REL_NS)
    }
    targets: dict[str, str] = {}
    for sheet in workbook.findall(".//x:sheets/x:sheet", X_NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib.get(f"{{{R_NS['r']}}}id")
        target = rel_map.get(rel_id, "")
        if target and not target.startswith("xl/"):
            target = f"xl/{target}"
        targets[name] = target
    return targets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(cell.find("x:is", X_NS).itertext()).strip() if cell.find("x:is", X_NS) is not None else ""
    raw = cell.findtext("x:v", default="", namespaces=X_NS)
    if not raw:
        return ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def col_index_from_ref(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha())
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch.upper()) - 64)
    return col


def read_sheet_rows(zf: zipfile.ZipFile, target: str, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(zf.read(target))
    rows_out: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", X_NS):
        values_by_col: dict[int, str] = {}
        max_col = 0
        for cell in row.findall("x:c", X_NS):
            ref = cell.attrib.get("r", "")
            col = col_index_from_ref(ref)
            max_col = max(max_col, col)
            values_by_col[col] = cell_value(cell, shared_strings)
        if max_col == 0:
            continue
        values = [values_by_col.get(idx, "") for idx in range(1, max_col + 1)]
        rows_out.append(values)
    return rows_out


def sheet_as_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [normalize(value) for value in rows[0]]
    dict_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows[1:], start=2):
        values = {headers[col]: normalize(row[col]) for col in range(min(len(headers), len(row))) if headers[col]}
        if any(values.values()):
            values["_row"] = str(idx)
            dict_rows.append(values)
    return dict_rows


def missing_review_fields(row: dict[str, str]) -> list[str]:
    return [field for field in REQUIRED_REVIEW_FIELDS if not normalize(row.get(field, ""))]


def infer_track(row: dict[str, str]) -> str:
    category = normalize(row.get("Category")).lower()
    planner_source = normalize(row.get("Planner Source")).lower()
    if category.startswith("turbobaba /") or planner_source.startswith("block "):
        return "TurboBaba narrative"
    if category.startswith("learning in public /"):
        return "Learning in public / workflow lessons"
    if planner_source == "bonus swap-in":
        return "Learning in public / workflow lessons"
    return "Unassigned"


def summarize_content_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    summary = {
        "total_rows": 0,
        "approved": 0,
        "disapproved": 0,
        "manual_seed": 0,
        "awaiting_review": 0,
        "backlog": 0,
        "drafting": 0,
        "ready": 0,
        "done": 0,
    }
    for row in rows:
        if not any(value for key, value in row.items() if key != "_row"):
            continue
        summary["total_rows"] += 1
        review_decision = canonical_review_decision(row.get("Review decision", ""))
        production_status = canonical_production_status(row)
        if review_decision == "Approved":
            summary["approved"] += 1
        if review_decision == "Disapproved":
            summary["disapproved"] += 1
        if review_decision == "MANUAL":
            summary["manual_seed"] += 1
        if not review_decision:
            summary["awaiting_review"] += 1
        if production_status == "Backlog":
            summary["backlog"] += 1
        elif production_status == "Drafting":
            summary["drafting"] += 1
        elif production_status == "Ready":
            summary["ready"] += 1
        elif production_status == "Done":
            summary["done"] += 1
    return summary


def review_workbook(workbook_path: Path, start: date, days: int) -> dict[str, object]:
    with zipfile.ZipFile(workbook_path) as zf:
        shared_strings = load_shared_strings(zf)
        targets = workbook_sheet_targets(zf)
        if CONTENT_SHEET not in targets:
            raise ValueError(f"Workbook is missing sheet: {CONTENT_SHEET}")
        if ARC_SHEET not in targets:
            raise ValueError(f"Workbook is missing sheet: {ARC_SHEET}")

        content_rows = sheet_as_dicts(read_sheet_rows(zf, targets[CONTENT_SHEET], shared_strings))
        arc_rows = sheet_as_dicts(read_sheet_rows(zf, targets[ARC_SHEET], shared_strings))

    end = start + timedelta(days=max(days, 1) - 1)
    upcoming_due: list[dict[str, str]] = []
    review_queue: list[dict[str, str]] = []
    refinement_required_queue: list[dict[str, str]] = []
    turbo_review_queue: list[dict[str, str]] = []
    learning_review_queue: list[dict[str, str]] = []
    unassigned_review_queue: list[dict[str, str]] = []
    manual_seed_queue: list[dict[str, str]] = []
    drafting_queue: list[dict[str, str]] = []
    in_progress_queue: list[dict[str, str]] = []
    ready_queue: list[dict[str, str]] = []
    done_queue: list[dict[str, str]] = []

    for values in content_rows:
        review_decision = canonical_review_decision(values.get("Review decision", ""))
        production_status = canonical_production_status(values)
        draft_doc = normalize(values.get("Draft doc"))
        missing_fields = missing_review_fields(values)
        track = infer_track(values)

        queue_item = {
            "id": values.get("ID", ""),
            "title": values.get("Title", ""),
            "review_decision": review_decision,
            "production_status": production_status,
            "category": values.get("Category", ""),
            "channel": values.get("Channel", ""),
            "draft_due": values.get("Draft due", ""),
            "review_due": values.get("Review due", ""),
            "scheduled_date": values.get("Scheduled date", ""),
            "draft_doc": draft_doc,
            "publish_status": values.get("Publish status", ""),
            "planner_source": values.get("Planner Source", ""),
            "track": track,
            "missing_fields": missing_fields,
            "row": values.get("_row", ""),
        }

        if not review_decision:
            if missing_fields:
                refinement_required_queue.append(queue_item)
            else:
                review_queue.append(queue_item)
                if track == "TurboBaba narrative":
                    turbo_review_queue.append(queue_item)
                elif track == "Learning in public / workflow lessons":
                    learning_review_queue.append(queue_item)
                else:
                    unassigned_review_queue.append(queue_item)
        elif review_decision == "MANUAL":
            manual_seed_queue.append(queue_item)

        if review_decision in {"Approved", "MANUAL"} and production_status == "Backlog":
            drafting_queue.append(queue_item)
        elif production_status == "Drafting":
            in_progress_queue.append(queue_item)
        elif production_status == "Ready":
            ready_queue.append(queue_item)
        elif production_status == "Done":
            done_queue.append(queue_item)

        for due_key in DUE_COLUMNS:
            candidate = parse_date(values.get(due_key, ""))
            if is_in_window(candidate, start, end):
                upcoming_due.append(
                    {
                        "id": values.get("ID", ""),
                        "title": values.get("Title", ""),
                        "due_type": due_key,
                        "due_date": candidate.isoformat() if candidate else "",
                        "review_decision": review_decision,
                        "production_status": production_status,
                        "publish_status": values.get("Publish status", ""),
                        "row": values.get("_row", ""),
                    }
                )

    upcoming_due.sort(key=lambda item: (item["due_date"], item["due_type"], item["id"]))
    summary = summarize_content_rows(content_rows)
    summary.update(
        {
            "review_ready": len(review_queue),
            "refinement_required": len(refinement_required_queue),
            "turbobaba_review": len(turbo_review_queue),
            "learning_review": len(learning_review_queue),
            "unassigned_review": len(unassigned_review_queue),
        }
    )
    return {
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": max(days, 1),
        },
        "workbook": str(workbook_path),
        "summary": summary,
        "upcoming_due": upcoming_due,
        "review_queue": review_queue,
        "refinement_required_queue": refinement_required_queue,
        "turbobaba_review_queue": turbo_review_queue,
        "learning_in_public_review_queue": learning_review_queue,
        "unassigned_review_queue": unassigned_review_queue,
        "manual_seed_queue": manual_seed_queue,
        "drafting_queue": drafting_queue,
        "in_progress_queue": in_progress_queue,
        "ready_queue": ready_queue,
        "done_queue": done_queue,
        "approvals_needed_now": review_queue,
        "refinement_needed_now": refinement_required_queue,
        "draft_queue": drafting_queue,
        "scheduling_gaps": ready_queue,
        "content_rows": content_rows,
        "month_arc_rows": arc_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review the fallback CONTENT workbook as a local stand-in for the LinkedIn control tower.")
    parser.add_argument("--workbook", required=True, help="Path to fallback CONTENT.xlsx")
    parser.add_argument("--days", type=int, default=7, help="Planning window length in days")
    parser.add_argument("--start-date", help="Start date in YYYY-MM-DD format. Defaults to today.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else date.today()
    payload = review_workbook(Path(args.workbook).expanduser().resolve(), start, args.days)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
