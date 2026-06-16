"""
Tier-based LLM client for Instagram Reels framework extraction and script writing.
Reads config from NOTION DIARY FETCHER/config.toml.
"""

import sys
import tomllib
from pathlib import Path

import httpx
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
}


def complete(prompt: str, section: str = "reel_extractor", dry_run: bool = False) -> tuple[str, str]:
    """Returns (content, model_used)."""
    cfg = load_config(section)

    if dry_run:
        print(prompt)
        sys.exit(0)

    provider = cfg.get("provider", "ollama")
    if provider == "openrouter":
        from openrouter.router import chat as llm_chat  # lazy — safe without API key at import time
        task = _TASK_MAP.get(section, section)
        messages = [{"role": "user", "content": prompt}]
        result = llm_chat(task, messages, max_tokens=2048)
        return result["content"], result.get("model", "openrouter:unknown")

    model = cfg["ollama_model"]
    endpoint = cfg["ollama_endpoint"].rstrip("/")
    return _ollama_complete(prompt, model, endpoint), f"ollama:{model}"


def _ollama_complete(prompt: str, model: str, endpoint: str) -> str:
    url = f"{endpoint}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except httpx.ConnectError:
        logger.error("Ollama not running — start with `ollama serve`")
        sys.exit(1)
    except httpx.TimeoutException:
        logger.error("Ollama timed out — model may be loading, try again")
        sys.exit(1)


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
# v2 vision hooks — present but inert until [reel_extractor.vision] enabled=true
# ---------------------------------------------------------------------------

def vision_describe(frame_paths: list, prompt: str, cfg: dict) -> str:
    if not cfg.get("enabled", False):
        raise NotImplementedError("vision tier disabled in v1.1 — set [reel_extractor.vision] enabled=true in config.toml")
    provider = cfg.get("provider", "anthropic")
    if provider == "anthropic":
        return _anthropic_vision(frame_paths, prompt, cfg)
    elif provider == "google":
        return _google_vision(frame_paths, prompt, cfg)
    else:
        raise ValueError(f"Unknown vision provider: {provider}")


def _anthropic_vision(frame_paths: list, prompt: str, cfg: dict) -> str:
    raise NotImplementedError("Anthropic vision provider — implement in v2")


def _google_vision(frame_paths: list, prompt: str, cfg: dict) -> str:
    raise NotImplementedError("Google vision provider — implement in v2")
