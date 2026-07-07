import re

def normalize_conflict_node(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def display_name_from_conflict_node(conflict_node: str) -> str:
    normalized = normalize_conflict_node(conflict_node)
    return " ".join(word.capitalize() for word in normalized.split("-"))