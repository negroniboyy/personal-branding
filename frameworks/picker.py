"""LLM-based framework picker.

Given an idea and a channel ("linkedin" | "reel"), asks a cheap model to pick
the best-fit framework from the full pool and explain why in one line.
Falls back to the existing keyword scorer on any failure (bad JSON, unknown
id, LLM error) so generation never blocks on the picker.
"""

import json
import re
import sqlite3
from typing import Optional


def _parse_json_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return [s.strip() for s in str(value).split(",") if s.strip()]


def _load_frameworks(conn: sqlite3.Connection, channel: str, video_format: Optional[str] = None) -> list[dict]:
    if channel == "linkedin":
        rows = conn.execute(
            "SELECT id, hook_type, tone, cta_type, description, fits_topics FROM frameworks"
        ).fetchall()
        return [dict(r) for r in rows]

    if video_format:
        rows = conn.execute(
            "SELECT id, hook_type, tone, cta_type, pacing, description, fits_topics FROM reel_frameworks "
            "WHERE COALESCE(video_format, 'talking_head') = ?",
            (video_format,),
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]
    rows = conn.execute(
        "SELECT id, hook_type, tone, cta_type, pacing, description, fits_topics FROM reel_frameworks"
    ).fetchall()
    return [dict(r) for r in rows]


def _format_pool(frameworks: list[dict]) -> str:
    lines = []
    for fw in frameworks:
        topics = ", ".join(_parse_json_list(fw.get("fits_topics")))
        parts = [f"id: {fw['id']}", f"hook: {fw.get('hook_type', '')}", f"tone: {fw.get('tone', '')}"]
        if "pacing" in fw:
            parts.append(f"pacing: {fw.get('pacing', '')}")
        parts.append(f"cta: {fw.get('cta_type', '')}")
        if topics:
            parts.append(f"topics: {topics}")
        if fw.get("description"):
            parts.append(f"desc: {fw['description']}")
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)


_PROMPT_TEMPLATE = """You are picking the best content framework for an idea. \
Read the idea and the list of available frameworks, then pick the ONE \
framework whose hook/tone/structure best fits the idea.

IDEA:
{idea}

AVAILABLE FRAMEWORKS:
{pool}

Respond with ONLY a JSON object, no other text:
{{"framework_id": "<the id you picked>", "reason": "<one sentence, why this framework fits this idea>"}}
"""


def _fallback(
    conn: sqlite3.Connection, channel: str, idea_prompt: Optional[str], video_format: Optional[str] = None
) -> tuple[str, str]:
    if channel == "linkedin":
        from content_writer.repository import get_frameworks
        from content_writer.recommender import score_frameworks
        scored = score_frameworks(get_frameworks(conn), idea_prompt)
        if not scored:
            raise ValueError("no linkedin frameworks available")
        return scored[0].id, "keyword-matched (picker fallback)"
    else:
        import sys
        from pathlib import Path
        fw_dir = Path(__file__).resolve().parent / "instagram_frameworks"
        if str(fw_dir) not in sys.path:
            sys.path.insert(0, str(fw_dir))
        import script_writer
        all_fw = script_writer.load_reel_frameworks(conn, video_format=video_format)
        if not all_fw:
            raise ValueError("no reel frameworks available")
        scored = script_writer.score_frameworks({}, all_fw, idea_prompt)
        return scored[0]["id"], "keyword-matched (picker fallback)"


def pick_framework(
    conn: sqlite3.Connection, channel: str, idea_prompt: str, video_format: Optional[str] = None
) -> tuple[str, str]:
    """Returns (framework_id, reason). Falls back to keyword scoring on any failure.
    video_format ('talking_head' | 'beat_edit') narrows the reel pool to matching-format
    frameworks, with a safe fallback to the unfiltered pool if none match — a tier's
    prompt template already constrains output shape regardless of which framework gets
    picked for pacing/scene-count, so a format mismatch degrades gracefully rather than
    blocking generation."""
    channel = "linkedin" if channel == "linkedin" else "reel"
    frameworks = _load_frameworks(conn, channel, video_format=video_format)
    if not frameworks:
        return _fallback(conn, channel, idea_prompt, video_format=video_format)

    try:
        from openrouter.router import chat as llm_chat
        prompt = _PROMPT_TEMPLATE.format(idea=idea_prompt, pool=_format_pool(frameworks))
        result = llm_chat("pick_framework", [{"role": "user", "content": prompt}], max_tokens=200)
        content = result["content"].strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError(f"no JSON in picker response: {content!r}")
        parsed = json.loads(match.group(0))
        framework_id = str(parsed["framework_id"])
        reason = str(parsed.get("reason", "")).strip()
        valid_ids = {str(fw["id"]) for fw in frameworks}
        if framework_id not in valid_ids:
            raise ValueError(f"picker chose unknown framework_id {framework_id!r}")
        return framework_id, reason or "picked by LLM"
    except Exception:
        return _fallback(conn, channel, idea_prompt, video_format=video_format)
