"""
Trusted pending conversational memory-action state.

XynaFaith owns confirmation-required memory-action state and
binds it to the authenticated user, conversation, exact logical
memory identity, trusted XynAssist source message, and stable
action execution request identifier.

Browser input never establishes this state.
"""

from sqlalchemy.orm import Session

from api.models.conversation_pending_memory_action import (
    ConversationPendingMemoryAction,
)


MEMORY_FORGET_ACTION = "memory.forget"


class ConversationPendingMemoryActionError(Exception):
    """Raised when pending memory-action state is invalid."""


def _normalize_required_string(
    value: str,
    *,
    maximum_length: int,
    error_message: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.strip()) > maximum_length
    ):
        raise ConversationPendingMemoryActionError(
            error_message
        )

    return value.strip()


def record_pending_memory_forget(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    memory_type: str,
    memory_key: str,
    source_message_id: str,
    action_request_id: str,
) -> ConversationPendingMemoryAction:
    """
    Record one trusted memory.forget confirmation request.

    A newer trusted proposal replaces the previous pending
    memory action for this authenticated user/conversation.
    The replacement includes a new stable action_request_id.
    """

    conversation_id = _normalize_required_string(
        conversation_id,
        maximum_length=36,
        error_message="Conversation is invalid",
    )

    memory_type = _normalize_required_string(
        memory_type,
        maximum_length=64,
        error_message="Memory type is invalid",
    )

    memory_key = _normalize_required_string(
        memory_key,
        maximum_length=255,
        error_message="Memory key is invalid",
    )

    source_message_id = _normalize_required_string(
        source_message_id,
        maximum_length=255,
        error_message=(
            "Conversation confirmation source is invalid"
        ),
    )

    action_request_id = _normalize_required_string(
        action_request_id,
        maximum_length=36,
        error_message=(
            "Memory action request is invalid"
        ),
    )

    pending = (
        db.query(ConversationPendingMemoryAction)
        .filter(
            ConversationPendingMemoryAction.user_id
            == user_id
        )
        .filter(
            ConversationPendingMemoryAction.conversation_id
            == conversation_id
        )
        .first()
    )

    if pending is None:
        pending = ConversationPendingMemoryAction(
            user_id=user_id,
            conversation_id=conversation_id,
            action_name=MEMORY_FORGET_ACTION,
            memory_type=memory_type,
            memory_key=memory_key,
            source_message_id=source_message_id,
            action_request_id=action_request_id,
        )
        db.add(pending)
    else:
        pending.action_name = MEMORY_FORGET_ACTION
        pending.memory_type = memory_type
        pending.memory_key = memory_key
        pending.source_message_id = source_message_id
        pending.action_request_id = action_request_id

    db.flush()

    return pending


def get_pending_memory_forget(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
) -> ConversationPendingMemoryAction | None:
    """
    Return trusted pending memory.forget state for the exact
    authenticated user and conversation.

    Missing or malformed state fails closed.
    """

    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        return None

    pending = (
        db.query(ConversationPendingMemoryAction)
        .filter(
            ConversationPendingMemoryAction.user_id
            == user_id
        )
        .filter(
            ConversationPendingMemoryAction.conversation_id
            == conversation_id.strip()
        )
        .first()
    )

    if pending is None:
        return None

    if (
        pending.action_name != MEMORY_FORGET_ACTION
        or not pending.memory_type
        or not pending.memory_key
        or not pending.source_message_id
        or not pending.action_request_id
    ):
        return None

    return pending


def consume_pending_memory_forget(
    *,
    db: Session,
    pending: ConversationPendingMemoryAction,
) -> None:
    """
    Remove pending confirmation after successful or replayed
    XynAssist execution.

    Caller owns the surrounding transaction.
    """

    db.delete(pending)
    db.flush()
