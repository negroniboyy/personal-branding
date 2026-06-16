"""Model router — cascades through primary → secondary → local Ollama."""
import yaml
import pathlib
from typing import AsyncGenerator

from shared.logger import get_logger
from .client import OpenRouterClient

logger = get_logger("narrative_warehouse")

_CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config" / "openrouter_models.yaml"

_client: OpenRouterClient | None = None


def _get_client() -> OpenRouterClient:
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


def _load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_model_chain(task_name: str) -> list[str]:
    config = _load_config()
    task = config["tasks"].get(task_name)
    if not task:
        raise ValueError(f"Unknown task: {task_name!r}. Add it to config/openrouter_models.yaml.")
    chain = [m for m in (task.get("primary"), task.get("secondary")) if m]
    chain.append(f"ollama:{task.get('local', 'gemma-32k:latest')}")
    return chain


def chat(
    task_name: str,
    messages: list,
    max_tokens: int = 1024,
    override_model: str = None,
    **opts,
) -> dict:
    chain = [override_model] if override_model else get_model_chain(task_name)
    last_error = None
    for model in chain:
        try:
            if model.startswith("ollama:"):
                return _call_ollama(model[len("ollama:"):], messages, max_tokens, **opts)
            result = _get_client().chat(model, messages, max_tokens, **opts)
            result["task"] = task_name
            logger.info(
                f"[openrouter] task={task_name} model={result['model']} "
                f"cost=${result['cost_usd']:.6f} tokens={result['tokens']['total']}"
            )
            return result
        except Exception as exc:
            logger.warning(f"[router] {model} failed: {exc} — trying next tier")
            last_error = exc
    raise RuntimeError(f"All models failed for task {task_name!r}. Last error: {last_error}")


async def stream(
    task_name: str,
    messages: list,
    max_tokens: int = 1024,
    override_model: str = None,
    **opts,
) -> AsyncGenerator[dict, None]:
    chain = [override_model] if override_model else get_model_chain(task_name)
    for model in chain:
        try:
            if model.startswith("ollama:"):
                async for chunk in _stream_ollama(model[len("ollama:"):], messages, max_tokens, **opts):
                    yield chunk
                return
            async for chunk in _get_client().stream(model, messages, max_tokens, **opts):
                yield chunk
            return
        except Exception as exc:
            logger.warning(f"[router] stream {model} failed: {exc} — trying next tier")
    raise RuntimeError(f"All streaming models failed for task {task_name!r}")


# ------------------------------------------------------------------
# Ollama shims — wired to frameworks/instagram_frameworks/llm_client
# ------------------------------------------------------------------

def _call_ollama(model: str, messages: list, max_tokens: int, **opts) -> dict:
    import httpx
    import time
    import tomllib
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "NOTION DIARY FETCHER" / "config.toml"
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    endpoint = cfg["ollama"]["base_url"].rstrip("/")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    start = time.time()
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(f"{endpoint}/api/chat", json=payload)
        resp.raise_for_status()
    latency_ms = int((time.time() - start) * 1000)
    content = resp.json()["message"]["content"]
    return {
        "model": f"ollama:{model}",
        "content": content,
        "latency_ms": latency_ms,
        "tokens": {"prompt": 0, "completion": 0, "total": 0},
        "cost_usd": 0.0,
        "finish_reason": "stop",
        "task": "",
    }


async def _stream_ollama(model: str, messages: list, max_tokens: int, **opts):
    import httpx
    import json
    import tomllib
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "NOTION DIARY FETCHER" / "config.toml"
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    endpoint = cfg["ollama"]["base_url"].rstrip("/")

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    content_buffer = ""
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", f"{endpoint}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                chunk_text = data.get("message", {}).get("content", "")
                if chunk_text:
                    content_buffer += chunk_text
                    yield {"type": "chunk", "text": chunk_text}
                if data.get("done"):
                    break

    yield {
        "type": "done",
        "model": f"ollama:{model}",
        "content": content_buffer,
        "latency_ms": 0,
        "tokens": {"prompt": 0, "completion": 0, "total": 0},
        "cost_usd": 0.0,
    }
