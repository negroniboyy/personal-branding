#!/usr/bin/env python3
"""Normalize the fallback CONTENT.xlsx workbook so it matches the live-sheet control-tower contract."""

from __future__ import annotations

import argparse
import json
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

from content_workbook import cell_value, ensure_headers, normalize, open_sheet_for_update, row_cell_map, row_elements, save_sheet, set_inline_cell, sheet_data_element  # noqa: E402


CONTENT_HEADERS = [
    "ID",
    "Title",
    "Content",
    "Review decision",
    "Category",
    "Channel",
    "Planner Source",
    "Production status",
    "Draft due",
    "Review due",
    "Scheduled date",
    "Draft doc",
    "Publish status",
    "Manager notes",
    "Published date",
    "Published URL",
]

ARC_HEADERS = [
    "ID",
    "Title",
    "When to post",
    "Angle",
    "Narrative spine",
    "Source fit",
    "Core tension",
    "Opening scene",
    "Notes",
    "Draft due",
    "Review due",
    "Scheduled date",
    "Production status",
]


def canonical_status(raw: str) -> str:
    value = normalize(raw).lower()
    if value == "backlog":
        return "Backlog"
    if value == "drafting":
        return "Drafting"
    if value == "ready":
        return "Ready"
    if value == "done":
        return "Done"
    return ""


def normalize_content_list(workbook_path: Path) -> dict[str, int]:
    doc = open_sheet_for_update(workbook_path, "Content List")
    header_map = ensure_headers(doc, CONTENT_HEADERS)
    sheet_data = sheet_data_element(doc.root)
    updated_rows = 0

    for row in row_elements(sheet_data):
        row_number = int(row.attrib.get("r", "0"))
        if row_number <= 1:
            continue
        cells = row_cell_map(row)
        values = {
            header: normalize(cell_value(cells[header_map[header]], doc.shared_strings))
            for header in header_map
            if header_map[header] in cells
        }
        if not any(values.values()):
            continue

        changed = False
        review_decision = normalize(values.get("Review decision"))
        if review_decision.lower() == "manual" and review_decision != "MANUAL":
            set_inline_cell(row, header_map["Review decision"], row_number, "MANUAL")
            changed = True

        production_status = canonical_status(values.get("Production status", ""))
        if not production_status:
            production_status = "Backlog"
        if values.get("Production status", "") != production_status:
            set_inline_cell(row, header_map["Production status"], row_number, production_status)
            changed = True

        if changed:
            updated_rows += 1

    save_sheet(doc)
    return {"content_list_rows_updated": updated_rows}


def normalize_month_arc(workbook_path: Path) -> dict[str, int]:
    doc = open_sheet_for_update(workbook_path, "Content Live")
    header_map = ensure_headers(doc, ARC_HEADERS)
    sheet_data = sheet_data_element(doc.root)
    updated_rows = 0

    for row in row_elements(sheet_data):
        row_number = int(row.attrib.get("r", "0"))
        if row_number <= 1:
            continue
        cells = row_cell_map(row)
        values = {
            header: normalize(cell_value(cells[header_map[header]], doc.shared_strings))
            for header in header_map
            if header_map[header] in cells
        }
        if not any(values.values()):
            continue

        production_status = canonical_status(values.get("Production status", ""))
        if not production_status:
            set_inline_cell(row, header_map["Production status"], row_number, "Backlog")
            updated_rows += 1
        elif values.get("Production status", "") != production_status:
            set_inline_cell(row, header_map["Production status"], row_number, production_status)
            updated_rows += 1

    save_sheet(doc)
    return {"month_arc_rows_updated": updated_rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, help="Path to fallback CONTENT.xlsx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workbook_path = Path(args.workbook).expanduser().resolve()
    stats = {}
    stats.update(normalize_content_list(workbook_path))
    stats.update(normalize_month_arc(workbook_path))
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
