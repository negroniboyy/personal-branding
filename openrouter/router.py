"""Model router — cascades through primary → secondary (OpenRouter only)."""
import yaml
import pathlib
from typing import AsyncGenerator

from shared.logger import get_logger
from .client import OpenRouterClient

logger = get_logger("openrouter")

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
    return [m for m in (task.get("primary"), task.get("secondary")) if m]


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
            async for chunk in _get_client().stream(model, messages, max_tokens, **opts):
                yield chunk
            return
        except Exception as exc:
            logger.warning(f"[router] stream {model} failed: {exc} — trying next tier")
    raise RuntimeError(f"All streaming models failed for task {task_name!r}")
