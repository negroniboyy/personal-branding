from typing import Optional
from pydantic import BaseModel


class Idea(BaseModel):
    id: str
    title: str
    body: str
    draft_count: int = 0
    created_at: str
    updated_at: str


class IdeaDraft(BaseModel):
    id: int
    channel: str  # "linkedin" | "reel"
    generated_text: str
    framework_id: Optional[str] = None
    story_node_id: Optional[str] = None
    model_used: str
    created_at: str


class IdeaWithDrafts(BaseModel):
    idea: Idea
    drafts: list[IdeaDraft]


class PatchIdeaRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


class GenerateDraftRequest(BaseModel):
    story_node_id: Optional[str] = None
    framework_id: Optional[str] = None
    idea_prompt: Optional[str] = None
