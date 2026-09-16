"""
Schemas for trusted XynaFaith conversation integration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from xynassist_service.actions.contracts import (
    is_supported_action,
)
from xynassist_service.actions.schemas import (
    ForgetMemoryArguments,
    RememberMemoryArguments,
)


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


class ConversationTurnCreate(BaseModel):
    request_id: str
    content: str
    context: dict | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ConversationAction(BaseModel):
    """
    Typed action proposal returned to a trusted product.

    This is a proposal only. XynAssist does not authorize or
    execute product mutations. The receiving product remains
    responsible for authentication, authorization, validation,
    confirmation, idempotency, and execution.
    """

    name: str
    arguments: dict = Field(default_factory=dict)

    model_config = ConfigDict(
        extra="forbid",
    )

    @field_validator("name")
    @classmethod
    def validate_action_name(
        cls,
        value: str,
    ) -> str:
        if not is_supported_action(
            value,
            product="xynafaith",
        ):
            raise ValueError(
                "Unsupported conversation action"
            )

        return value

    @field_validator("arguments")
    @classmethod
    def validate_action_arguments(
        cls,
        value: dict,
        info,
    ) -> dict:
        name = info.data.get("name")

        if name in {
            "sermon.save",
            "sermon.update",
            "sermon.delete",
        }:
            if value:
                raise ValueError(
                    "Sermon action arguments must be empty"
                )

            return value

        if name == "memory.remember":
            validated = (
                RememberMemoryArguments
                .model_validate(value)
            )

            return validated.model_dump()

        if name == "memory.forget":
            validated = (
                ForgetMemoryArguments
                .model_validate(value)
            )

            return validated.model_dump()

        return value


class ConversationTurnResponse(BaseModel):
    conversation: ConversationDetailResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
    skill: str | None = None

    # Compatibility fields used by XynaFaith action handling.
    user_message_id: str | None = None
    action: ConversationAction | None = None
    prompt: str | None = None
