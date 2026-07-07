from typing import Optional
from pydantic import BaseModel


class Idea(BaseModel):
    id: str
    title: str
    body: str
    draft_count: int = 0
    created_at: str
    updated_at: str
    notion_page_id: Optional[str] = None
    pillar: Optional[str] = None
    tier: Optional[str] = None
    channels: list[str] = []


class IdeaDraft(BaseModel):
    id: int
    channel: str  # "linkedin" | "reel"
    generated_text: str
    framework_id: Optional[str] = None
    framework_pick_reason: Optional[str] = None
    story_node_id: Optional[str] = None
    model_used: str
    created_at: str
    version: int = 1
    tier: Optional[str] = None


class IdeaWithDrafts(BaseModel):
    idea: Idea
    drafts: list[IdeaDraft]


class PatchIdeaRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


class PatchIdeaTierRequest(BaseModel):
    tier: str


class GenerateDraftRequest(BaseModel):
    story_node_id: Optional[str] = None
    framework_id: Optional[str] = None
    idea_prompt: Optional[str] = None
