#!/usr/bin/env python3
"""
Collect PersonalBrand LinkedIn drafting sources from local repo artifacts into a single markdown dump.

This helper reads the repo's markdown, DOCX, and XLSX planning artifacts and
prints a consolidated markdown report that can be pasted into model context or
used for quick inspection. It does not read the live Google Sheet directly.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
X_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
R_NS = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
PKG_REL_NS = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def read_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    for paragraph in root.findall(".//w:p", W_NS):
        text = "".join(paragraph.itertext()).strip()
        if text:
            paragraphs.append(" ".join(text.split()))
    return "\n".join(paragraphs)


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(".//x:si", X_NS):
        text = "".join(item.itertext()).strip()
        values.append(" ".join(text.split()))
    return values


def workbook_sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(".//pr:Relationship", PKG_REL_NS)
    }

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall(".//x:sheets/x:sheet", X_NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib.get(f"{{{R_NS['r']}}}id")
        target = rel_map.get(rel_id, "")
        if target and not target.startswith("xl/"):
            target = f"xl/{target}"
        sheets.append((name, target))
    return sheets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        inline = cell.find("x:is", X_NS)
        return "".join(inline.itertext()).strip() if inline is not None else ""
    raw = cell.findtext("x:v", default="", namespaces=X_NS)
    if not raw:
        return ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def read_xlsx(path: Path, max_rows: int) -> list[dict[str, object]]:
    sheets_out: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as zf:
        shared_strings = load_shared_strings(zf)
        for sheet_name, target in workbook_sheet_targets(zf):
            if not target or target not in zf.namelist():
                continue
            root = ET.fromstring(zf.read(target))
            rows_out: list[list[str]] = []
            for row in root.findall(".//x:sheetData/x:row", X_NS):
                values = [cell_value(cell, shared_strings).strip() for cell in row.findall("x:c", X_NS)]
                if any(values):
                    rows_out.append(values)
                if len(rows_out) >= max_rows:
                    break
            sheets_out.append({"sheet": sheet_name, "rows": rows_out})
    return sheets_out


def discover_sources(root: Path) -> list[tuple[str, Path]]:
    ordered: list[tuple[str, Path]] = []

    def add_if_exists(label: str, relative_path: str) -> None:
        path = root / relative_path
        if path.exists():
            ordered.append((label, path))

    add_if_exists("brandbook", "brandguide/brandbook.md")
    add_if_exists("linkedin-guide", "brandguide/linkedin.md")

    for path in sorted((root / "brandguide").glob("*.docx")) if (root / "brandguide").exists() else []:
        ordered.append(("brandguide-docx", path))

    for path in sorted((root / "contents").glob("*.xlsx")) if (root / "contents").exists() else []:
        ordered.append(("content-plan-xlsx", path))

    for path in sorted((root / "contents").glob("*.docx")) if (root / "contents").exists() else []:
        ordered.append(("content-draft-docx", path))

    for path in sorted((root / "Posts").glob("*.docx")) if (root / "Posts").exists() else []:
        ordered.append(("post-progress-docx", path))

    add_if_exists("draft-template", "templates/gpts/draft-writer.md")
    add_if_exists("post-brief-template", "templates/google/post-brief-template.md")
    add_if_exists("monthly-strategy-template", "templates/google/monthly-strategy-brief.md")
    return ordered


def render_markdown(root: Path, max_rows: int) -> str:
    lines = [f"# LinkedIn Source Dump", "", f"Repo root: `{root}`", ""]
    for label, path in discover_sources(root):
        rel = path.relative_to(root)
        lines.append(f"## {label}: `{rel}`")
        lines.append("")
        if path.suffix.lower() == ".md":
            lines.append(read_markdown(path))
        elif path.suffix.lower() == ".docx":
            lines.append(read_docx(path))
        elif path.suffix.lower() == ".xlsx":
            for sheet in read_xlsx(path, max_rows=max_rows):
                lines.append(f"### Sheet: {sheet['sheet']}")
                rows = sheet["rows"]
                if not rows:
                    lines.append("_No non-empty rows found._")
                    lines.append("")
                    continue
                for row in rows:
                    lines.append(" | ".join(row))
                lines.append("")
        else:
            lines.append("_Unsupported file type._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(root: Path, max_rows: int) -> str:
    payload: dict[str, object] = {"root": str(root), "sources": []}
    for label, path in discover_sources(root):
        rel = str(path.relative_to(root))
        if path.suffix.lower() == ".md":
            content: object = read_markdown(path)
        elif path.suffix.lower() == ".docx":
            content = read_docx(path)
        elif path.suffix.lower() == ".xlsx":
            content = read_xlsx(path, max_rows=max_rows)
        else:
            content = None
        payload["sources"].append({"label": label, "path": rel, "content": content})
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Repo root containing brandguide/, contents/, Posts/, and templates/")
    parser.add_argument("--max-sheet-rows", type=int, default=8, help="Maximum non-empty rows to preview per worksheet")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"[ERROR] Root does not exist: {root}", file=sys.stderr)
        return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    output = render_json(root, args.max_sheet_rows) if args.json else render_markdown(root, args.max_sheet_rows)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
