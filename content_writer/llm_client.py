import json
from typing import Optional

import urllib.request
import urllib.error

_OLLAMA_HOST = "http://localhost:11434"


def generate_ollama(
    prompt: str,
    model: str = "gemma3:latest",
    host: str = _OLLAMA_HOST,
) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    return body.get("response", "").strip()


def generate_openai(prompt: str, model: str) -> str:  # noqa: ARG001
    raise NotImplementedError("501 — OpenAI provider not implemented in v1")


def generate_anthropic(prompt: str, model: str) -> str:  # noqa: ARG001
    raise NotImplementedError("501 — Anthropic provider not implemented in v1")


def generate(
    prompt: str,
    provider: str = "ollama",
    model: str = "gemma3:latest",
    ollama_host: Optional[str] = None,
) -> str:
    if provider == "ollama":
        return generate_ollama(prompt, model=model, host=ollama_host or _OLLAMA_HOST)
    if provider == "openai":
        return generate_openai(prompt, model)
    if provider == "anthropic":
        return generate_anthropic(prompt, model)
    raise ValueError(f"Unknown provider: {provider}")
