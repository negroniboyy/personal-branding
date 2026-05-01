#!/usr/bin/env python3
"""Append proposal rows to the local CONTENT.xlsx fallback mirror.

The input proposal file must be JSON and contain a list of objects with keys:
id, title, content, category, channel, planner_source

A legacy proposal_id key is also accepted and mapped into the ID column.
"""

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

from content_workbook import append_dense_row, cell_value, ensure_headers, normalize, open_sheet_for_update, save_sheet, sheet_data_element, row_elements, row_cell_map  # noqa: E402


REQUIRED_HEADERS = [
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


def load_proposals(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Proposal file must contain a JSON list")
    proposals: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each proposal must be a JSON object")
        row_id = normalize(item.get("id") or item.get("proposal_id"))
        proposal = {
            "ID": row_id,
            "Title": normalize(item.get("title")),
            "Content": normalize(item.get("content")),
            "Review decision": "",
            "Category": normalize(item.get("category")),
            "Channel": normalize(item.get("channel") or "LinkedIn") or "LinkedIn",
            "Planner Source": normalize(item.get("planner_source")),
            "Production status": "Backlog",
            "Draft due": "",
            "Review due": "",
            "Scheduled date": "",
            "Draft doc": "",
            "Publish status": "",
            "Manager notes": "",
            "Published date": "",
            "Published URL": "",
        }
        if not proposal["Title"] or not proposal["ID"]:
            raise ValueError("Each proposal must include a non-empty title and id")
        proposals.append(proposal)
    return proposals


def append_rows(workbook_path: Path, sheet_name: str, proposals: list[dict[str, str]]) -> int:
    doc = open_sheet_for_update(workbook_path, sheet_name)
    headers = ensure_headers(doc, REQUIRED_HEADERS)
    id_col = headers["ID"]
    sheet_data = sheet_data_element(doc.root)

    existing_ids: set[str] = set()
    last_data_row = 1
    for row in row_elements(sheet_data):
        row_number = int(row.attrib.get("r", "0"))
        if row_number <= 1:
            continue
        cells = row_cell_map(row)
        row_values = {
            header: normalize(cell_value(cells[headers[header]], doc.shared_strings))
            for header in headers
            if headers[header] in cells
        }
        if id_col in cells:
            raw_id = normalize(cell_value(cells[id_col], doc.shared_strings))
            if raw_id:
                existing_ids.add(raw_id)
        if any(row_values.values()):
            last_data_row = max(last_data_row, row_number)

    appended = 0
    for proposal in proposals:
        if proposal["ID"] in existing_ids:
            continue
        row = last_data_row + 1
        append_dense_row(doc, row, headers, proposal)
        appended += 1
        existing_ids.add(proposal["ID"])
        last_data_row = row

    save_sheet(doc)
    return appended


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, help="Path to local fallback CONTENT.xlsx workbook")
    parser.add_argument("--sheet", default="Content List", help="Sheet name to append to")
    parser.add_argument("--proposal-file", required=True, help="JSON file containing proposal rows")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workbook_path = Path(args.workbook).expanduser().resolve()
    proposal_file = Path(args.proposal_file).expanduser().resolve()

    if not workbook_path.exists():
        print(f"[ERROR] Workbook not found: {workbook_path}", file=sys.stderr)
        return 1
    if not proposal_file.exists():
        print(f"[ERROR] Proposal file not found: {proposal_file}", file=sys.stderr)
        return 1

    proposals = load_proposals(proposal_file)
    appended = append_rows(workbook_path, args.sheet, proposals)
    print(f"appended_rows={appended}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
