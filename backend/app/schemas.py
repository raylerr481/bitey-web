from typing import Any
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    message: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    conversation_id: str
    answer: str
    research_required: bool
    research_reasons: list[str]
    providers: list[str]
