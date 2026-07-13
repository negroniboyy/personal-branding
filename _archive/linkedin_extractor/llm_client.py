"""
Tier-based LLM client for content framework extraction.
Routes to Ollama local by default; other tiers are placeholders.
"""

import sys
import httpx
from shared.logger import get_logger

logger = get_logger("linkedin_frameworks")

TIER_CONFIG = {
    "local": {
        "provider": "ollama",
        "model": "gemma-32k:latest",
        "endpoint": "http://localhost:11434",
    },
    "cheap_cloud": None,   # NotImplementedError
    "vision": None,        # NotImplementedError
    "premium": None,       # NotImplementedError
}

_PROMPT_TEMPLATE_PATH = None  # set by extract_linkedin.py before calling complete()


def _load_prompt_template() -> str:
    if _PROMPT_TEMPLATE_PATH is None:
        raise ValueError("Prompt template path not set. Call set_prompt_template_path() first.")
    with open(_PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def set_prompt_template_path(path: str) -> None:
    global _PROMPT_TEMPLATE_PATH
    _PROMPT_TEMPLATE_PATH = path


def complete(prompt: str, tier: str = "local", dry_run: bool = False) -> str:
    """
    Send a prompt to the configured LLM tier.
    If dry_run=True, print the rendered prompt and exit without calling the LLM.
    """
    cfg = TIER_CONFIG.get(tier)
    if cfg is None:
        if tier in TIER_CONFIG:
            raise NotImplementedError(f"Tier '{tier}' is not implemented yet.")
        raise ValueError(f"Unknown tier: '{tier}'")

    if dry_run:
        print(prompt)
        sys.exit(0)

    provider = cfg["provider"]
    model = cfg["model"]
    endpoint = cfg["endpoint"].rstrip("/")

    if provider == "ollama":
        return _ollama_complete(prompt, model, endpoint)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _ollama_complete(prompt: str, model: str, endpoint: str) -> str:
    url = f"{endpoint}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
    except httpx.ConnectError:
        logger.error("Ollama not running — start with `ollama serve`")
        sys.exit(1)
    except httpx.TimeoutException:
        logger.error("Ollama timed out — model may be loading, try again or increase timeout")
        sys.exit(1)


def inject_post_text(prompt_template: str, post_text: str) -> str:
    """Replace {{POST_TEXT}} placeholder in the prompt template."""
    return prompt_template.replace("{{POST_TEXT}}", post_text)