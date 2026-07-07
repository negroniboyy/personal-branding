from typing import Optional

from .models import Framework


def score_frameworks(
    frameworks: list[Framework],
    idea_prompt: Optional[str],
) -> list[Framework]:
    idea_words = _tokenise(idea_prompt)

    for fw in frameworks:
        topics = {t.lower() for t in fw.fits_topics}
        s = 1.0 if (idea_words and topics & idea_words) else 0.0
        fw.score = s

    return sorted(frameworks, key=lambda f: f.score, reverse=True)


def _tokenise(text: Optional[str]) -> set[str]:
    if not text:
        return set()
    return {w.lower() for w in text.replace(",", " ").split() if len(w) > 2}
