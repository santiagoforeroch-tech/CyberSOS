from pydantic import BaseModel, Field

from app.schemas.reports import CATEGORIES


class AgentMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AgentChatRequest(BaseModel):
    messages: list[AgentMessage] = Field(min_length=1, max_length=20)
    conversation_id: str | None = None


class AgentDraft(BaseModel):
    category: str | None = None
    priority: str = "Media"
    summary: str = ""
    facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    evidence_requested: list[str] = Field(default_factory=list)
    needs_human_review: bool = True


class AgentChatResponse(BaseModel):
    conversation_id: str | None = None
    message: str
    draft: AgentDraft
    ready_to_confirm: bool = False
