from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from api.core.dependencies import get_current_user
from api.models.user import User
from api.services.xynassist_client import (
    XynAssistClient,
    XynAssistError,
)


router = APIRouter()


class ConversationCreate(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=255,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ConversationTurnCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=50_000,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


def conversation_service_unavailable(
    exc: XynAssistError,
) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "Conversation service is "
            "temporarily unavailable"
        ),
    )


@router.post(
    "/conversations",
    status_code=201,
)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        return await XynAssistClient().create_conversation(
            external_user_id=str(
                current_user.id
            ),
            title=payload.title,
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc


@router.get(
    "/conversations",
)
async def list_conversations(
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        return await XynAssistClient().list_conversations(
            external_user_id=str(
                current_user.id
            ),
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc


@router.get(
    "/conversations/{conversation_id}",
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        return await XynAssistClient().get_conversation(
            external_user_id=str(
                current_user.id
            ),
            conversation_id=conversation_id,
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc


@router.post(
    "/conversations/{conversation_id}/turns",
)
async def execute_conversation_turn(
    conversation_id: str,
    payload: ConversationTurnCreate,
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        return (
            await XynAssistClient()
            .execute_conversation_turn(
                external_user_id=str(
                    current_user.id
                ),
                conversation_id=conversation_id,
                content=payload.content,
            )
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc
