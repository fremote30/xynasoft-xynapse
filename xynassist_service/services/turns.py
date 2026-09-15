"""
Transactional XynAssist conversation-turn execution.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from xynassist_service.models.message import (
    ConversationMessage,
)
from xynassist_service.schemas.conversations import (
    ConversationDetailResponse,
    ConversationTurnResponse,
    MessageResponse,
)
from xynassist_service.services.conversations import (
    PRODUCT_XYNAFAITH,
    get_conversation,
    list_messages,
)
from xynassist_service.services.turn_engine import (
    execute_turn_engine,
)
from xynassist_service.services.turn_idempotency import (
    TurnRequestConflict,
    TurnRequestInProgress,
    TurnRequestStateError,
    claim_turn_request,
    complete_turn_request,
    fail_turn_request,
)


class ConversationTurnNotFound(Exception):
    """Conversation does not exist for the trusted user."""


def _conversation_detail(
    db: Session,
    *,
    conversation,
) -> ConversationDetailResponse:
    return ConversationDetailResponse(
        id=conversation.id,
        product=conversation.product,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=list_messages(
            db,
            conversation_id=conversation.id,
        ),
    )


def execute_conversation_turn(
    db: Session,
    *,
    external_user_id: str,
    conversation_id: str,
    request_id: str,
    content: str,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Execute exactly one logical conversation turn.

    Completed retries return the persisted response without invoking
    the turn engine again.
    """

    conversation = get_conversation(
        db,
        external_user_id=external_user_id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise ConversationTurnNotFound(
            "Conversation not found"
        )

    claim = claim_turn_request(
        db,
        product=PRODUCT_XYNAFAITH,
        external_user_id=external_user_id,
        conversation_id=conversation_id,
        request_id=request_id,
        content=content,
        context=context,
    )

    if claim.is_replay:
        return claim.replay_response

    # Persist the processing claim before expensive AI work.
    # PostgreSQL advisory locking makes this the single-winner
    # execution boundary.
    db.commit()

    try:
        engine_result = execute_turn_engine(
            content=content,
            context=context,
        )
    except Exception:
        try:
            # Reattach the persisted turn after the prior commit.
            turn = db.merge(claim.turn)

            fail_turn_request(
                db,
                turn=turn,
                error_code="turn_engine_failure",
            )

            db.commit()
        except Exception:
            db.rollback()

        raise

    try:
        turn = db.merge(claim.turn)

        user_message = ConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=content,
            skill=engine_result.skill,
        )

        assistant_message = ConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="assistant",
            content=engine_result.content,
            skill=engine_result.skill,
        )

        db.add_all(
            [
                user_message,
                assistant_message,
            ]
        )

        db.flush()

        # Refresh conversation state in this transaction.
        conversation = get_conversation(
            db,
            external_user_id=external_user_id,
            conversation_id=conversation_id,
        )

        detail = _conversation_detail(
            db,
            conversation=conversation,
        )

        response = ConversationTurnResponse(
            conversation=detail,
            user_message=MessageResponse.model_validate(
                user_message
            ),
            assistant_message=MessageResponse.model_validate(
                assistant_message
            ),
            skill=engine_result.skill,
            user_message_id=user_message.id,
            action=engine_result.action,
            prompt=engine_result.prompt,
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

        complete_turn_request(
            db,
            turn=turn,
            response=response,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
        )

        db.commit()

        return response
    except Exception:
        db.rollback()
        raise
