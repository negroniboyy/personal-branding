import json
import re
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

SYSTEM_PROMPT = """You are a narrative analyst. Given a person's diary entry, extract 4 story variables and assign thematic tags.

OUTPUT: Return ONLY valid JSON, no markdown, no explanation.
{
  "user_state": "...",
  "conflict_node": "...",
  "desired_outcome": "...",
  "the_bridge": "...",
  "thematic_tags": ["tag1", "tag2", "tag3"],
  "worth_score": 0.85,
  "narrative_flag": "Normal"
}

FIELD REQUIREMENTS:
- user_state: 2-10 words, the mindset/situation
- conflict_node: 2-10 words, reusable phrase for clustering (e.g. "imposter-syndrome", "creative-block")
- desired_outcome: 2-10 words, what they want
- the_bridge: 2-10 words, what they believe will get them there
- thematic_tags: 2-3 lowercase tags, single-word or hyphenated

SCORING (0.0–1.0):
- 1.0: Explicit struggle, clear goal, emotional tension, concrete details
- 0.7-0.9: Some tension, identifiable desire, meaningful context
- 0.4-0.6: Vague/abstract, no clear conflict
- 0.1-0.3: Pure factual log, no emotional weight
- narrative_flag = "Low Narrative Potential" when worth_score < 0.4
"""


@dataclass
class ExtractionResult:
    user_state: str
    conflict_node: str
    desired_outcome: str
    the_bridge: str
    thematic_tags: list[str]
    worth_score: float
    narrative_flag: Literal["Normal", "Low Narrative Potential"]


class LLMClient(ABC):
    @abstractmethod
    def extract_story_variables(self, diary_text: str) -> ExtractionResult:
        ...


class MinimaxCloudClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "MiniMax-Text-01",
        base_url: str = "https://api.minimax.io",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def extract_story_variables(self, diary_text: str) -> ExtractionResult:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"DIARY ENTRY:\n---\n{diary_text}\n---"},
            ],
            "temperature": 0.3,
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        return self._parse(content)

    def _parse(self, content: str) -> ExtractionResult:
        text = content.strip() if hasattr(content, "strip") else content.strip()
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            text = re.sub(r"^```json\s*", "", text.strip())
            text = re.sub(r"\s*```$", "", text.strip())
            obj = json.loads(text)
        return ExtractionResult(
            user_state=obj["user_state"],
            conflict_node=obj["conflict_node"],
            desired_outcome=obj["desired_outcome"],
            the_bridge=obj["the_bridge"],
            thematic_tags=obj["thematic_tags"],
            worth_score=float(obj["worth_score"]),
            narrative_flag=obj["narrative_flag"],
        )


class OllamaClient(LLMClient):
    def __init__(
        self,
        model: str = "gemma4",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def extract_story_variables(self, diary_text: str) -> ExtractionResult:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"DIARY ENTRY:\n---\n{diary_text}\n---"},
            ],
            "stream": False,
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["message"]["content"]
        return self._parse(content)

    def _parse(self, content: str) -> ExtractionResult:
        text = content.strip() if hasattr(content, "strip") else content.strip()
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            text = re.sub(r"^```json\s*", "", text.strip())
            text = re.sub(r"\s*```$", "", text.strip())
            obj = json.loads(text)
        return ExtractionResult(
            user_state=obj["user_state"],
            conflict_node=obj["conflict_node"],
            desired_outcome=obj["desired_outcome"],
            the_bridge=obj["the_bridge"],
            thematic_tags=obj["thematic_tags"],
            worth_score=float(obj["worth_score"]),
            narrative_flag=obj["narrative_flag"],
        )


def make_llm_client(provider: str, model: str | None = None) -> LLMClient:
    if provider == "minimax":
        from .config import MinimaxConfig
        cfg = MinimaxConfig()
        if not cfg.api_key:
            raise ValueError("MINIMAX_API_KEY environment variable is not set")
        return MinimaxCloudClient(cfg.api_key, model or cfg.model_name, cfg.base_url)
    elif provider == "ollama":
        from .config import OllamaConfig
        cfg = OllamaConfig()
        return OllamaClient(model or cfg.default_model, cfg.base_url)
    else:
        raise ValueError(f"Unknown provider: {provider}")