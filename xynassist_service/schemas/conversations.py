"""
Schemas for trusted XynaFaith conversation integration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: str
    product: str
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    skill: str | None
    created_at: datetime


class ConversationDetailResponse(
    ConversationResponse,
):
    messages: list[MessageResponse]
