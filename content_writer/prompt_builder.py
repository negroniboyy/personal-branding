from pathlib import Path

from .models import Framework


_VOICE_BLOCK_PATH = Path(__file__).resolve().parent.parent / "brandguide" / "voice_dna_block.txt"


def _voice_block() -> str:
    return _VOICE_BLOCK_PATH.read_text(encoding="utf-8")


def build_freeform_prompt(
    idea_prompt: str,
    framework: Framework,
) -> str:
    parts = [
        "You are a LinkedIn content writer writing in the creator's own VOICE.",
        "",
        "The source material below is already a refined, single-thread insight the creator wrote",
        "himself — not a raw diary dump. Do not hunt for a thread or pad it out; it is already the",
        "one idea. Sharpen it in his voice using the craft moves below. Stay strictly inside its",
        "facts — invent nothing beyond what it says.",
        "",
        "---",
        "",
        _voice_block(),
        "",
        "---",
        "",
        "## Framework (shape only — its example topics are from a different story)",
        f"Name: {framework.name}",
        f"Hook type: {framework.hook_type}",
        f"Tone: {framework.tone}",
        f"Paragraph style: {framework.paragraph_style}",
        f"Argument pattern: {framework.argument_pattern}",
        f"CTA: {framework.cta}",
        "",
        "## Source material (this is the entire idea — write from it, do not invent unrelated facts)",
        idea_prompt,
        "",
        "## Instructions",
        "- Follow the framework structure strictly, filtered through the VOICE DNA above.",
        "- The source material IS the creator's refined idea — sharpen it, do not replace or pad it.",
        "- Apply the tone and paragraph style throughout, but never let it become preachy or salesy.",
        "- The framework's CTA is a SHAPE hint only. Never write \"DM me\", \"link in bio\", \"comment",
        "  below\", \"follow for more\", or any sell. Prefer one honest question or his current state.",
        "- Apply craft moves 1 (hook with a foil) and 5 (meta-payoff) — required.",
        "- Use whitespace between paragraphs.",
        "- Do not exceed 1300 characters.",
        "- Output the post only, no commentary.",
    ]
    return "\n".join(parts)
