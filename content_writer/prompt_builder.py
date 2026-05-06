from typing import Optional

from .models import Framework, StoryNode

_MAX_SOURCE_CHARS = 12_000


def build_prompt(
    story: StoryNode,
    framework: Framework,
    chunks: list[str],
    idea_prompt: Optional[str] = None,
    max_source_chars: int = _MAX_SOURCE_CHARS,
) -> str:
    source_text = _assemble_source(story, chunks, max_source_chars)

    parts = [
        f"You are a LinkedIn content writer. Write a post using the structure below.",
        "",
        "## Framework",
        f"Name: {framework.name}",
        f"Hook type: {framework.hook_type}",
        f"Tone: {framework.tone}",
        f"Paragraph style: {framework.paragraph_style}",
        f"Argument pattern: {framework.argument_pattern}",
        f"CTA: {framework.cta}",
        "",
        "## Source material",
        source_text,
    ]

    if idea_prompt:
        parts += ["", "## Framing hint (optional, use only to guide angle)", idea_prompt]

    parts += [
        "",
        "## Instructions",
        "- Follow the framework structure strictly.",
        "- Use the source material as the only factual basis.",
        "- Apply the tone and paragraph style throughout.",
        "- End with the CTA.",
        "- Use whitespace between paragraphs.",
        "- Do not exceed 1300 characters.",
        "- Output the post only, no commentary.",
    ]

    return "\n".join(parts)


def _assemble_source(story: StoryNode, chunks: list[str], max_chars: int) -> str:
    header = (
        f"[{story.title}]\n"
        f"Situation: {story.user_state}\n"
        f"Tension: {story.conflict_node}\n"
        f"Outcome: {story.desired_outcome}\n"
        f"Insight: {story.the_bridge}\n"
    )
    budget = max_chars - len(header)
    assembled_chunks = []
    used = 0
    for chunk in chunks:
        prefixed = f"[{story.title}] {chunk}"
        if used + len(prefixed) > budget:
            break
        assembled_chunks.append(prefixed)
        used += len(prefixed)

    return header + "\n".join(assembled_chunks)
