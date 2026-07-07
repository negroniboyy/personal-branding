"""OpenRouter client — thin wrapper over the OpenAI SDK compatibility layer."""
import os
import time
import asyncio
from typing import AsyncGenerator

import openai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "NOTION DIARY FETCHER", ".env"))

from shared.logger import get_logger

logger = get_logger("openrouter")


class OpenRouterClient:
    def __init__(self):
        api_key = os.environ["OPENROUTER_API_KEY"]
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": os.environ.get("APP_REFERER", "http://localhost:8000"),
                "X-Title": os.environ.get("APP_TITLE", "PersonalBrandStudio"),
            },
        )

    def _call_with_retry(self, model: str, fn, max_attempts: int = 4):
        delays = [30, 60, 120]
        for attempt in range(max_attempts):
            try:
                return fn()
            except openai.RateLimitError as exc:
                if attempt == max_attempts - 1:
                    raise
                retry_after = None
                if hasattr(exc, "response") and exc.response is not None:
                    retry_after = exc.response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else delays[attempt]
                logger.warning(f"[rate limit] {model} — waiting {wait:.0f}s (attempt {attempt + 1})")
                time.sleep(wait)
            except (openai.APIConnectionError, openai.APITimeoutError):
                if attempt == max_attempts - 1:
                    raise
                time.sleep(delays[attempt])

    def chat(self, model: str, messages: list, max_tokens: int = 1024, **opts) -> dict:
        def _call():
            start = time.time()
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **opts,
            )
            latency_ms = int((time.time() - start) * 1000)
            if not response.choices:
                raise RuntimeError(f"No choices from {model}")
            choice = response.choices[0]
            usage = response.usage
            cost_usd = 0.0
            if usage and usage.model_extra:
                cost_usd = float(usage.model_extra.get("cost", 0.0))
            return {
                "model": response.model,
                "content": choice.message.content or "",
                "latency_ms": latency_ms,
                "tokens": {
                    "prompt": usage.prompt_tokens if usage else 0,
                    "completion": usage.completion_tokens if usage else 0,
                    "total": usage.total_tokens if usage else 0,
                },
                "cost_usd": cost_usd,
                "finish_reason": choice.finish_reason or "",
            }

        return self._call_with_retry(model, _call)

    async def stream(
        self, model: str, messages: list, max_tokens: int = 1024, **opts
    ) -> AsyncGenerator[dict, None]:
        loop = asyncio.get_event_loop()
        start = time.time()

        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                stream=True,
                **opts,
            ),
        )

        content_buffer = ""
        usage_data = {}

        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                content_buffer += delta.content
                yield {"type": "chunk", "text": delta.content}
            if hasattr(chunk, "usage") and chunk.usage:
                usage_data = chunk.usage

        latency_ms = int((time.time() - start) * 1000)
        cost_usd = 0.0
        if usage_data and hasattr(usage_data, "model_extra") and usage_data.model_extra:
            cost_usd = float(usage_data.model_extra.get("cost", 0.0))

        yield {
            "type": "done",
            "model": model,
            "content": content_buffer,
            "latency_ms": latency_ms,
            "tokens": {
                "prompt": getattr(usage_data, "prompt_tokens", 0),
                "completion": getattr(usage_data, "completion_tokens", 0),
                "total": getattr(usage_data, "total_tokens", 0),
            },
            "cost_usd": cost_usd,
        }
