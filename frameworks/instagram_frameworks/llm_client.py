"""
Tier-based LLM client for Instagram Reels framework extraction and script writing.
Reads config from NOTION DIARY FETCHER/config.toml.
"""

import sys
import tomllib
from pathlib import Path

from shared.logger import get_logger

logger = get_logger("instagram_frameworks")

# Config lives two levels up: frameworks/instagram_frameworks/ → frameworks/ → personal_brand/
# then into NOTION DIARY FETCHER/config.toml
_CONFIG_PATH = Path(__file__).parent.parent.parent / "NOTION DIARY FETCHER" / "config.toml"


def load_config(section: str) -> dict:
    with open(_CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)
    # Support dotted section keys like "reel_extractor.vision"
    parts = section.split(".")
    node = data
    for part in parts:
        node = node[part]
    return node


_TASK_MAP = {
    "script_writer": "generate_reel_script",
    "reel_extractor": "extract_reel_framework",
    "reel_extractor_beat_edit": "extract_reel_framework_beat_edit",
}


def complete(prompt: str, section: str = "reel_extractor", dry_run: bool = False) -> tuple[str, str]:
    """Returns (content, model_used)."""
    cfg = load_config(section)

    if dry_run:
        print(prompt)
        sys.exit(0)

    from openrouter.router import chat as llm_chat  # lazy — safe without API key at import time
    task = _TASK_MAP.get(section, section)
    messages = [{"role": "user", "content": prompt}]
    result = llm_chat(task, messages, max_tokens=2048)
    return result["content"], result.get("model", "openrouter:unknown")


def inject(template: str, **placeholders: str) -> str:
    result = template
    for key, value in placeholders.items():
        token = "{{" + key + "}}"
        result = result.replace(token, value)
    # Check for unfilled tokens
    import re
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", result)
    if remaining:
        raise ValueError(f"Unfilled template tokens: {remaining}")
    return result


# ---------------------------------------------------------------------------
# Vision — beat-edit reference extraction (frame + prompt -> structured YAML)
# ---------------------------------------------------------------------------

def _encode_image(path) -> str:
    import base64
    data = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{data}"


def complete_vision(prompt: str, frame_paths: list, section: str = "reel_extractor_beat_edit") -> tuple[str, str]:
    """Multimodal completion: text prompt + ordered frame images. Returns (content, model_used).
    Routes through the standard OpenRouter cascade (config/openrouter_models.yaml) — no separate
    provider/credential path, same as every other task in this module."""
    content = [{"type": "text", "text": prompt}]
    for p in frame_paths:
        content.append({"type": "image_url", "image_url": {"url": _encode_image(p)}})

    from openrouter.router import chat as llm_chat
    task = _TASK_MAP.get(section, section)
    result = llm_chat(task, [{"role": "user", "content": content}], max_tokens=1200)
    return result["content"], result.get("model", "openrouter:unknown")
