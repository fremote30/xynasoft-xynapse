from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from api.core.dependencies import (
    get_current_user,
    get_db,
)
from sqlalchemy.orm import Session

from api.models.user import User
from api.services.conversation_actions import (
    ConversationActionContextError,
    UnsupportedConversationActionError,
    execute_conversation_action,
)
from api.services.conversation_pending_actions import (
    ConversationPendingActionError,
    SERMON_DELETE_ACTION,
    get_pending_sermon_delete,
    record_pending_sermon_delete,
)
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


class ConversationSermonContext(BaseModel):
    """
    Current XynaFaith sermon state supplied for a
    conversational sermon action.

    Identity and ownership are intentionally absent.
    """

    id: int | None = Field(
        default=None,
        ge=1,
    )

    data: dict[str, Any]

    model_config = ConfigDict(
        extra="forbid",
    )


class ConversationTurnCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=50_000,
    )

    request_id: UUID

    sermon: ConversationSermonContext | None = None

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
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    sermon_context = payload.sermon

    trusted_context = None
    pending = None

    if sermon_context is not None:
        trusted_context = {
            "active_resource": "sermon",
            "resource_persisted": (
                sermon_context.id is not None
            ),
        }

        pending = get_pending_sermon_delete(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            sermon_id=sermon_context.id,
        )

        if pending is not None:
            trusted_context["pending_action"] = (
                SERMON_DELETE_ACTION
            )

    try:
        result = (
            await XynAssistClient()
            .execute_conversation_turn(
                external_user_id=str(
                    current_user.id
                ),
                conversation_id=conversation_id,
                content=payload.content,
                context=trusted_context,
            )
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc

    action = result.get(
        "action"
    )

    if action is None:
        return result

    if not isinstance(action, dict):
        raise HTTPException(
            status_code=502,
            detail=(
                "Conversation service returned "
                "an invalid action"
            ),
        )

    source_message_id = result.get(
        "user_message_id"
    )

    if (
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Conversation service returned "
                "an invalid action"
            ),
        )

    # Confirmation-required actions are pending state, not
    # executable product mutations. Bind the request to the
    # exact authenticated product resource before returning
    # the confirmation prompt to the browser.
    prompt = result.get("prompt")

    if prompt is not None:
        if (
            not isinstance(prompt, str)
            or not prompt.strip()
            or action.get("name")
            != SERMON_DELETE_ACTION
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Conversation service returned "
                    "an invalid confirmation"
                ),
            )

        try:
            record_pending_sermon_delete(
                db=db,
                user_id=current_user.id,
                conversation_id=conversation_id,
                sermon_id=(
                    sermon_context.id
                    if sermon_context
                    else None
                ),
                source_message_id=source_message_id,
            )
        except ConversationPendingActionError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Conversation confirmation could not "
                    "be recorded"
                ),
            ) from exc

        return result

    try:
        executed_action = execute_conversation_action(
            db=db,
            user_id=current_user.id,
            request_id=str(payload.request_id),
            source_message_id=source_message_id,
            action=action,
            sermon_id=(
                sermon_context.id
                if sermon_context
                else None
            ),
            sermon_data=(
                sermon_context.data
                if sermon_context
                else None
            ),
            bound_sermon_id=(
                pending.resource_id
                if (
                    action.get("name")
                    == SERMON_DELETE_ACTION
                    and pending is not None
                )
                else None
            ),
            pending_action=(
                pending
                if (
                    action.get("name")
                    == SERMON_DELETE_ACTION
                    and pending is not None
                )
                else None
            ),
        )
    except (
        UnsupportedConversationActionError,
        ConversationActionContextError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Conversation action could not "
                "be completed"
            ),
        ) from exc

    return {
        **result,
        "action": executed_action,
    }
