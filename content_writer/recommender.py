from typing import Optional

from .models import Framework, StoryNode


def score_stories(
    nodes: list[StoryNode],
    weekly_index: Optional[dict],
    idea_prompt: Optional[str],
) -> list[StoryNode]:
    weekly_themes: set[str] = set()
    if weekly_index:
        raw = weekly_index.get("thread_summary_json") or weekly_index.get("themes") or ""
        if isinstance(raw, str):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    weekly_themes = {t.lower() for t in parsed}
                elif isinstance(parsed, dict):
                    weekly_themes = {t.lower() for t in parsed.get("themes", [])}
            except (json.JSONDecodeError, TypeError):
                weekly_themes = {t.strip().lower() for t in raw.split(",") if t.strip()}

    idea_words: set[str] = _tokenise(idea_prompt)

    for node in nodes:
        s = node.worth_score
        tags = {t.lower() for t in node.thematic_tags}
        if weekly_themes and tags & weekly_themes:
            s += 2.0
        if idea_words and tags & idea_words:
            s += 1.0
        node.score = s

    return sorted(nodes, key=lambda n: n.score, reverse=True)


def score_frameworks(
    frameworks: list[Framework],
    story: StoryNode,
    idea_prompt: Optional[str],
) -> list[Framework]:
    story_tags = {t.lower() for t in story.thematic_tags}
    idea_words = _tokenise(idea_prompt)

    for fw in frameworks:
        topics = {t.lower() for t in fw.fits_topics}
        s = len(story_tags & topics) * 1.0
        if idea_words and topics & idea_words:
            s += 1.0
        fw.score = s

    return sorted(frameworks, key=lambda f: f.score, reverse=True)


def _tokenise(text: Optional[str]) -> set[str]:
    if not text:
        return set()
    return {w.lower() for w in text.replace(",", " ").split() if len(w) > 2}
