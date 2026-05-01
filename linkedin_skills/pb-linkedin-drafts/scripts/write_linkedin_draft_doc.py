#!/usr/bin/env python3
"""
Write a minimal editable LinkedIn draft .docx file.

The input is a JSON payload containing the draft metadata and the generated
draft text. The script writes a local Word document so the user can fine-tune
the copy manually outside the chat transcript.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import escape


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

PACKAGE_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

DOCUMENT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_only).strip("-").lower()
    return slug or "draft"


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return cleaned or "draft"


def split_paragraphs(value: str) -> list[str]:
    text = value.replace("\r\n", "\n").strip()
    if not text:
        return []
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]


def make_run(text: str, *, bold: bool = False, size: int | None = None) -> str:
    escaped = escape(text)
    props: list[str] = []
    if bold:
        props.append("<w:b/>")
    if size is not None:
        props.append(f'<w:sz w:val="{size}"/>')
    if props:
        return f"<w:r><w:rPr>{''.join(props)}</w:rPr><w:t xml:space=\"preserve\">{escaped}</w:t></w:r>"
    return f"<w:r><w:t xml:space=\"preserve\">{escaped}</w:t></w:r>"


def make_paragraph(text: str = "", *, bold: bool = False, size: int | None = None) -> str:
    if not text:
        return "<w:p/>"
    return f"<w:p>{make_run(text, bold=bold, size=size)}</w:p>"


def body_paragraphs(text: str) -> list[str]:
    return [make_paragraph(paragraph) for paragraph in split_paragraphs(text)]


def build_document_xml(payload: dict[str, object]) -> str:
    post_id = str(payload.get("post_id") or payload.get("id") or "").strip()
    paragraphs: list[str] = []
    if post_id:
        paragraphs.append(make_paragraph(f"ID: {post_id}", bold=True, size=24))
        paragraphs.append(make_paragraph())
    paragraphs.extend(body_paragraphs(str(payload.get("primary_draft") or "")))

    body = "".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:w10="urn:schemas-microsoft-com:office:word"
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
 xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
 xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
 xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
 xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
 mc:Ignorable="w14 wp14">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def build_core_xml(title: str) -> str:
    created = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_title = escape(title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{safe_title}</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>
"""


APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>
"""


def determine_output_path(payload: dict[str, object], output: str | None, output_dir: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    if not output_dir:
        raise ValueError("Either --output or --output-dir must be provided.")
    out_dir = Path(output_dir).expanduser().resolve()
    post_id = safe_id(str(payload.get("post_id") or payload.get("id") or "draft").strip())
    title_slug = slugify(str(payload.get("title") or "LinkedIn Draft").strip())
    filename = f"LinkedIn Draft - {post_id} - {title_slug}.docx"
    return out_dir / filename


def write_docx(output_path: Path, payload: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title = str(payload.get("title") or "LinkedIn Draft").strip()
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", PACKAGE_RELS_XML)
        zf.writestr("word/document.xml", build_document_xml(payload))
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_XML)
        zf.writestr("docProps/core.xml", build_core_xml(title))
        zf.writestr("docProps/app.xml", APP_XML)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-file", required=True, help="Path to the JSON payload describing the draft.")
    parser.add_argument("--output", help="Exact .docx output path.")
    parser.add_argument("--output-dir", help="Directory where the script should create a default-named .docx file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload_path = Path(args.json_file).expanduser().resolve()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    output_path = determine_output_path(payload, args.output, args.output_dir)
    write_docx(output_path, payload)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
