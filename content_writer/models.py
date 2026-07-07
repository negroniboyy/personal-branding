from dataclasses import dataclass
from typing import Optional


@dataclass
class Framework:
    id: str
    name: str
    hook_type: str
    tone: str
    paragraph_style: str
    cta: str
    argument_pattern: str
    fits_topics: list[str]
    description: str = ""
    score: float = 0.0  # computed ranking score


@dataclass
class ContentDraft:
    story_node_id: Optional[str]
    framework_id: str
    generated_text: str
    model_used: str
    id: Optional[int] = None
    idea_prompt: Optional[str] = None
    created_at: Optional[str] = None
    framework_pick_reason: Optional[str] = None


@dataclass
class RecommendationRequest:
    idea_prompt: Optional[str] = None
    top_n: int = 20
    domain: Optional[str] = None


@dataclass
class RecommendationResult:
    stories: list
    frameworks: list[Framework]


@dataclass
class GenerateRequest:
    framework_id: str
    idea_prompt: Optional[str] = None
    provider: str = "openrouter"
    model: Optional[str] = None  # None -> use config/openrouter_models.yaml cascade


@dataclass
class GenerateResult:
    draft_id: int
    generated_text: str
    story_node_id: Optional[str]
    framework_id: str
    model_used: str
    framework_pick_reason: Optional[str] = None
