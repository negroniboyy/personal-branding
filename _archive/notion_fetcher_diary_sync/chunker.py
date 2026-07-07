from .database import _extract_plain_text

CHARS_PER_TOKEN = 4


def chunk_page_blocks(
    blocks: list[dict],
    title: str,
    chunk_size_tokens: int = 500,
    overlap_chars: int = 50,
) -> list[str]:
    """Split page blocks into overlapping text chunks prefixed with page title."""
    chunk_size_chars = chunk_size_tokens * CHARS_PER_TOKEN

    text_parts = []
    for block in blocks:
        plain_text = _extract_plain_text(block)
        if plain_text and plain_text.strip():
            text_parts.append(plain_text.strip())

    full_text = "\n\n".join(text_parts)
    if not full_text:
        return []

    prefix = f"[{title}] " if title else ""
    chunks = []
    start = 0

    while start < len(full_text):
        chunk_body = full_text[start : start + chunk_size_chars]
        chunks.append(prefix + chunk_body)
        start += chunk_size_chars - overlap_chars
        if start >= len(full_text):
            break

    return chunks
