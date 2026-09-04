"""
Trusted pending conversational action state.

XynaFaith owns confirmation-required action state and binds
it to the authenticated user, conversation, and exact
product resource before any destructive action can execute.
"""

from sqlalchemy.orm import Session

from api.models.conversation_pending_action import (
    ConversationPendingAction,
)


SERMON_DELETE_ACTION = "sermon.delete"
SERMON_RESOURCE = "sermon"


class ConversationPendingActionError(Exception):
    """Raised when pending action state is invalid."""


def record_pending_sermon_delete(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    sermon_id: int | None,
    source_message_id: str,
) -> ConversationPendingAction:
    """
    Record a pending sermon deletion for the exact saved
    sermon active when confirmation was requested.

    The authenticated user and route conversation establish
    ownership. Browser-controlled action identity is never
    accepted here.
    """
    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        raise ConversationPendingActionError(
            "Conversation is invalid"
        )

    if (
        not isinstance(sermon_id, int)
        or isinstance(sermon_id, bool)
        or sermon_id < 1
    ):
        raise ConversationPendingActionError(
            "A saved sermon is required for deletion"
        )

    if (
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise ConversationPendingActionError(
            "Conversation confirmation source is invalid"
        )

    conversation_id = conversation_id.strip()
    source_message_id = source_message_id.strip()

    pending = (
        db.query(ConversationPendingAction)
        .filter(
            ConversationPendingAction.user_id
            == user_id
        )
        .filter(
            ConversationPendingAction.conversation_id
            == conversation_id
        )
        .first()
    )

    if pending is None:
        pending = ConversationPendingAction(
            user_id=user_id,
            conversation_id=conversation_id,
            action_name=SERMON_DELETE_ACTION,
            resource_type=SERMON_RESOURCE,
            resource_id=sermon_id,
            source_message_id=source_message_id,
        )

        db.add(pending)

    else:
        # A newer confirmation request replaces the previous
        # pending action for this authenticated conversation.
        pending.action_name = SERMON_DELETE_ACTION
        pending.resource_type = SERMON_RESOURCE
        pending.resource_id = sermon_id
        pending.source_message_id = source_message_id

    db.commit()

    return pending


def get_pending_sermon_delete(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    sermon_id: int | None,
) -> ConversationPendingAction | None:
    """
    Return the pending sermon deletion only when it belongs
    to the authenticated user and conversation and remains
    bound to the exact currently active saved sermon.

    A missing, stale, malformed, or resource-mismatched
    pending action fails closed by returning None.
    """
    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        return None

    if (
        not isinstance(sermon_id, int)
        or isinstance(sermon_id, bool)
        or sermon_id < 1
    ):
        return None

    pending = (
        db.query(ConversationPendingAction)
        .filter(
            ConversationPendingAction.user_id
            == user_id
        )
        .filter(
            ConversationPendingAction.conversation_id
            == conversation_id.strip()
        )
        .first()
    )

    if pending is None:
        return None

    if (
        pending.action_name != SERMON_DELETE_ACTION
        or pending.resource_type != SERMON_RESOURCE
        or pending.resource_id != sermon_id
    ):
        return None

    return pending
