"""
Trusted XynaFaith conversational action execution.

XynAssist may request an allowlisted product action, but
XynaFaith remains responsible for authentication,
authorization, validation, idempotency, and application
state changes.
"""

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models.conversation_action_execution import (
    ConversationActionExecution,
)
from api.models.conversation_pending_action import (
    ConversationPendingAction,
)
from api.services.sermon_persistence import (
    SermonNotFoundError,
    build_sermon_delete_for_user,
    build_sermon_for_user,
    build_sermon_update_for_user,
)


SERMON_SAVE_ACTION = "sermon.save"
SERMON_UPDATE_ACTION = "sermon.update"
SERMON_DELETE_ACTION = "sermon.delete"


class UnsupportedConversationActionError(Exception):
    """Raised when XynAssist requests an unknown action."""


class ConversationActionContextError(Exception):
    """Raised when an action lacks required product context."""


def _find_execution(
    *,
    db: Session,
    user_id: int,
    request_id: str,
) -> ConversationActionExecution | None:
    return (
        db.query(
            ConversationActionExecution
        )
        .filter(
            ConversationActionExecution.user_id
            == user_id
        )
        .filter(
            ConversationActionExecution.request_id
            == request_id
        )
        .first()
    )


def _execution_response(
    execution: ConversationActionExecution,
) -> dict[str, Any]:
    return {
        "name": execution.action_name,
        "status": execution.status,
        "result": execution.result,
    }


def _validate_existing_execution(
    *,
    execution: ConversationActionExecution,
    action_name: str,
) -> None:
    if execution.action_name != action_name:
        raise ConversationActionContextError(
            "Conversation action idempotency conflict"
        )


def execute_conversation_action(
    *,
    db: Session,
    user_id: int,
    request_id: str,
    source_message_id: str,
    action: dict[str, Any],
    sermon_id: int | None,
    sermon_data: dict[str, Any] | None,
    bound_sermon_id: int | None = None,
    pending_action: ConversationPendingAction | None = None,
) -> dict[str, Any]:
    """
    Execute one allowlisted conversational product action.

    The authenticated XynaFaith user plus XynaFaith's
    stable request identifier form the durable idempotency
    key. The XynAssist user-message identifier is retained
    separately for provenance.

    Identity is supplied by authenticated request context
    and is never read from the action envelope.
    """
    if (
        not isinstance(request_id, str)
        or not request_id.strip()
        or len(request_id.strip()) > 36
    ):
        raise ConversationActionContextError(
            "Conversation action request is invalid"
        )

    request_id = request_id.strip()

    if (
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise ConversationActionContextError(
            "Conversation action source is invalid"
        )

    source_message_id = source_message_id.strip()

    action_name = action.get("name")

    if action_name not in {
        SERMON_SAVE_ACTION,
        SERMON_UPDATE_ACTION,
        SERMON_DELETE_ACTION,
    }:
        raise UnsupportedConversationActionError(
            "Unsupported conversation action"
        )

    arguments = action.get(
        "arguments",
        {},
    )

    if (
        not isinstance(arguments, dict)
        or arguments
    ):
        raise ConversationActionContextError(
            f"{action_name} does not accept arguments"
        )

    if (
        action_name in {
            SERMON_SAVE_ACTION,
            SERMON_UPDATE_ACTION,
        }
        and sermon_data is None
    ):
        raise ConversationActionContextError(
            "Current sermon context is required"
        )

    if (
        action_name == SERMON_SAVE_ACTION
        and sermon_id is not None
    ):
        raise ConversationActionContextError(
            "sermon.save requires an unsaved sermon"
        )

    if (
        action_name == SERMON_UPDATE_ACTION
        and sermon_id is None
    ):
        raise ConversationActionContextError(
            "sermon.update requires a saved sermon"
        )

    existing = _find_execution(
        db=db,
        user_id=user_id,
        request_id=request_id,
    )

    if existing is not None:
        _validate_existing_execution(
            execution=existing,
            action_name=action_name,
        )

        return _execution_response(
            existing
        )

    if action_name == SERMON_DELETE_ACTION:
        if (
            not isinstance(bound_sermon_id, int)
            or isinstance(bound_sermon_id, bool)
            or bound_sermon_id < 1
        ):
            raise ConversationActionContextError(
                "sermon.delete requires a trusted "
                "bound sermon"
            )

        if (
            pending_action is None
            or pending_action.user_id != user_id
            or pending_action.action_name
            != SERMON_DELETE_ACTION
            or pending_action.resource_type != "sermon"
            or pending_action.resource_id
            != bound_sermon_id
        ):
            raise ConversationActionContextError(
                "sermon.delete requires trusted "
                "pending confirmation"
            )

    if action_name == SERMON_SAVE_ACTION:
        sermon = build_sermon_for_user(
            db=db,
            user_id=user_id,
            payload=sermon_data,
        )
    elif action_name == SERMON_UPDATE_ACTION:
        try:
            sermon = build_sermon_update_for_user(
                db=db,
                user_id=user_id,
                sermon_id=sermon_id,
                payload=sermon_data,
            )
        except SermonNotFoundError as exc:
            raise ConversationActionContextError(
                "Sermon not found"
            ) from exc
    else:
        try:
            sermon = build_sermon_delete_for_user(
                db=db,
                user_id=user_id,
                sermon_id=bound_sermon_id,
            )
        except SermonNotFoundError as exc:
            raise ConversationActionContextError(
                "Sermon not found"
            ) from exc

    execution = ConversationActionExecution(
        user_id=user_id,
        request_id=request_id,
        source_message_id=source_message_id,
        action_name=action_name,
        status="completed",
        result={
            "sermon_id": sermon.id,
        },
    )

    db.add(execution)

    if action_name == SERMON_DELETE_ACTION:
        db.delete(pending_action)

    try:
        # Product mutation, execution record, and any consumed
        # destructive confirmation become durable together.
        db.commit()

    except IntegrityError:
        # A concurrent request may have completed the same
        # action first. Roll back our sermon insert and load
        # the winning durable execution.
        db.rollback()

        existing = _find_execution(
            db=db,
            user_id=user_id,
            request_id=request_id,
        )

        if existing is None:
            raise

        _validate_existing_execution(
            execution=existing,
            action_name=action_name,
        )

        return _execution_response(
            existing
        )

    return _execution_response(
        execution
    )
