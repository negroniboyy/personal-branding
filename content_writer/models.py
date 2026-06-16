from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StoryNode:
    id: str
    title: str
    user_state: str
    conflict_node: str
    desired_outcome: str
    the_bridge: str
    thematic_tags: list[str]
    worth_score: float
    score: float = 0.0  # computed ranking score, not persisted


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


@dataclass
class RecommendationRequest:
    idea_prompt: Optional[str] = None
    top_n: int = 20
    domain: Optional[str] = None


@dataclass
class RecommendationResult:
    stories: list[StoryNode]
    frameworks: list[Framework]


@dataclass
class GenerateRequest:
    story_node_id: Optional[str]
    framework_id: str
    idea_prompt: Optional[str] = None
    provider: str = "ollama"
    model: str = "gemma3:latest"


@dataclass
class GenerateResult:
    draft_id: int
    generated_text: str
    story_node_id: Optional[str]
    framework_id: str
    model_used: str
