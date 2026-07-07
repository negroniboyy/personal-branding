"""Notion <-> PBS idea field mapping for the CONTENT database.

Pillar/Tier are optional select properties — absent until Max adds them to the
database in Notion (PRD v3.0 §4 groundwork); missing properties map to None,
never a failure.
"""

LIFECYCLE_TO_NOTION_STATUS = {
    "queued": "Not started",
    "drafted": "Script ready",
    "approved": "Script ready",
    "recorded": "In progress",
    "posted": "Done",
    "killed": "Killed",
}


_TEXT_BLOCK_TYPES = (
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item", "quote", "callout", "toggle", "to_do",
)


def _plain_text(rich_text: list[dict]) -> str:
    return "".join(t.get("plain_text", "") for t in (rich_text or []))


def blocks_to_text(blocks: list[dict]) -> str:
    """Flatten a page's body blocks to plain text, in document order. Used as a
    fallback source for idea body when the Description property is empty —
    many ideas are written directly in the page body, not that property."""
    lines = []
    for block in blocks:
        block_type = block.get("type")
        if block_type not in _TEXT_BLOCK_TYPES:
            continue
        text = _plain_text((block.get(block_type) or {}).get("rich_text", []))
        if text:
            lines.append(text)
    return "\n".join(lines)


def page_to_idea_fields(page: dict) -> dict:
    props = page.get("properties", {})

    title = _plain_text((props.get("Name") or {}).get("title", []))
    body = _plain_text((props.get("Description") or {}).get("rich_text", []))
    channels = [opt["name"] for opt in ((props.get("Select") or {}).get("multi_select") or [])]

    pillar_prop = (props.get("Pillar") or {}).get("select")
    pillar = pillar_prop["name"] if pillar_prop else None

    tier_prop = (props.get("Tier") or {}).get("select")
    tier = tier_prop["name"] if tier_prop else None

    return {
        "notion_page_id": page["id"],
        "title": title,
        "body": body,
        "channels": channels,
        "pillar": pillar,
        "tier": tier,
    }
