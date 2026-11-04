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

SERVICE_ASSIGNMENT_CREATE_ACTION = "service_assignment.create"
SERVICE_ASSIGNMENT_REASSIGN_ACTION = (
    "service_assignment.reassign"
)
SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION = (
    "service_assignment.update_status"
)
SERVICE_ASSIGNMENT_RESOURCE = "service_assignment"


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

def record_pending_service_assignment(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    church_id: int,
    arguments: dict,
    source_message_id: str,
    action_request_id: str,
) -> ConversationPendingAction:
    """
    Bind confirmation to one exact service-assignment proposal.

    The stored arguments become authoritative for later confirmed
    execution. A later model/browser payload cannot replace them.
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
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise ConversationPendingActionError(
            "Conversation confirmation source is invalid"
        )

    if (
        not isinstance(action_request_id, str)
        or not action_request_id.strip()
        or len(action_request_id.strip()) > 36
    ):
        raise ConversationPendingActionError(
            "Action request is invalid"
        )

    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        raise ConversationPendingActionError(
            "Trusted Church Space context is required"
        )

    required = {
        "event_id",
        "group_id",
        "church_membership_id",
        "service_role",
    }

    if not isinstance(arguments, dict) or set(arguments) != required:
        raise ConversationPendingActionError(
            "Service assignment arguments are invalid"
        )

    for key in (
        "event_id",
        "group_id",
        "church_membership_id",
    ):
        value = arguments.get(key)

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ConversationPendingActionError(
                "Service assignment arguments are invalid"
            )

    service_role = arguments.get("service_role")

    if (
        not isinstance(service_role, str)
        or not service_role.strip()
        or len(service_role.strip()) > 120
    ):
        raise ConversationPendingActionError(
            "Service assignment arguments are invalid"
        )

    normalized_arguments = {
        "event_id": arguments["event_id"],
        "group_id": arguments["group_id"],
        "church_membership_id": arguments[
            "church_membership_id"
        ],
        "service_role": service_role.strip(),
    }

    conversation_id = conversation_id.strip()
    source_message_id = source_message_id.strip()
    action_request_id = action_request_id.strip()

    pending = (
        db.query(ConversationPendingAction)
        .filter(
            ConversationPendingAction.user_id == user_id
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
            action_name=SERVICE_ASSIGNMENT_CREATE_ACTION,
            resource_type=SERVICE_ASSIGNMENT_RESOURCE,
            resource_id=arguments["event_id"],
            source_message_id=source_message_id,
            arguments=normalized_arguments,
            action_request_id=action_request_id,
            church_id=church_id,
        )
        db.add(pending)

    else:
        pending.action_name = SERVICE_ASSIGNMENT_CREATE_ACTION
        pending.resource_type = SERVICE_ASSIGNMENT_RESOURCE
        pending.resource_id = arguments["event_id"]
        pending.source_message_id = source_message_id
        pending.arguments = normalized_arguments
        pending.action_request_id = action_request_id
        pending.church_id = church_id

    db.commit()
    return pending


def get_pending_service_assignment(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    church_id: int,
) -> ConversationPendingAction | None:
    """
    Return only a complete service-assignment pending binding.
    """
    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        return None

    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        return None

    pending = (
        db.query(ConversationPendingAction)
        .filter(
            ConversationPendingAction.user_id == user_id
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
        pending.church_id != church_id
        or pending.action_name != SERVICE_ASSIGNMENT_CREATE_ACTION
        or pending.resource_type != SERVICE_ASSIGNMENT_RESOURCE
        or not isinstance(pending.arguments, dict)
        or not pending.action_request_id
    ):
        return None

    return pending


def record_pending_service_assignment_reassignment(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    church_id: int,
    arguments: dict,
    source_message_id: str,
    action_request_id: str,
) -> ConversationPendingAction:
    """Bind confirmation to one exact service reassignment."""
    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        raise ConversationPendingActionError(
            "Conversation is invalid"
        )

    if (
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise ConversationPendingActionError(
            "Conversation confirmation source is invalid"
        )

    if (
        not isinstance(action_request_id, str)
        or not action_request_id.strip()
        or len(action_request_id.strip()) > 36
    ):
        raise ConversationPendingActionError(
            "Action request is invalid"
        )

    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        raise ConversationPendingActionError(
            "Trusted Church Space context is required"
        )

    required = {
        "event_id",
        "assignment_id",
        "group_id",
        "church_membership_id",
        "service_role",
    }

    if (
        not isinstance(arguments, dict)
        or set(arguments) != required
    ):
        raise ConversationPendingActionError(
            "Service assignment reassignment arguments are invalid"
        )

    for key in (
        "event_id",
        "assignment_id",
        "group_id",
        "church_membership_id",
    ):
        value = arguments.get(key)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ConversationPendingActionError(
                "Service assignment reassignment arguments are invalid"
            )

    service_role = arguments.get("service_role")
    if (
        not isinstance(service_role, str)
        or not service_role.strip()
        or len(service_role.strip()) > 120
    ):
        raise ConversationPendingActionError(
            "Service assignment reassignment arguments are invalid"
        )

    normalized_arguments = {
        "event_id": arguments["event_id"],
        "assignment_id": arguments["assignment_id"],
        "group_id": arguments["group_id"],
        "church_membership_id": arguments["church_membership_id"],
        "service_role": service_role.strip(),
    }

    conversation_id = conversation_id.strip()
    source_message_id = source_message_id.strip()
    action_request_id = action_request_id.strip()

    pending = (
        db.query(ConversationPendingAction)
        .filter(ConversationPendingAction.user_id == user_id)
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
            action_name=SERVICE_ASSIGNMENT_REASSIGN_ACTION,
            resource_type=SERVICE_ASSIGNMENT_RESOURCE,
            resource_id=arguments["assignment_id"],
            source_message_id=source_message_id,
            arguments=normalized_arguments,
            action_request_id=action_request_id,
            church_id=church_id,
        )
        db.add(pending)
    else:
        pending.action_name = SERVICE_ASSIGNMENT_REASSIGN_ACTION
        pending.resource_type = SERVICE_ASSIGNMENT_RESOURCE
        pending.resource_id = arguments["assignment_id"]
        pending.source_message_id = source_message_id
        pending.arguments = normalized_arguments
        pending.action_request_id = action_request_id
        pending.church_id = church_id

    db.commit()
    return pending


def get_pending_service_assignment_reassignment(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    church_id: int,
) -> ConversationPendingAction | None:
    """Return only an exact pending service reassignment."""
    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        return None

    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        return None

    pending = (
        db.query(ConversationPendingAction)
        .filter(ConversationPendingAction.user_id == user_id)
        .filter(
            ConversationPendingAction.conversation_id
            == conversation_id.strip()
        )
        .first()
    )

    if pending is None:
        return None

    if (
        pending.church_id != church_id
        or pending.action_name != SERVICE_ASSIGNMENT_REASSIGN_ACTION
        or pending.resource_type != SERVICE_ASSIGNMENT_RESOURCE
        or not isinstance(pending.arguments, dict)
        or not pending.action_request_id
        or pending.resource_id
        != pending.arguments.get("assignment_id")
    ):
        return None

    return pending


def record_pending_service_assignment_status_update(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    church_id: int,
    arguments: dict,
    source_message_id: str,
    action_request_id: str,
) -> ConversationPendingAction:
    """
    Bind confirmation to one exact assignment status transition.
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
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise ConversationPendingActionError(
            "Conversation confirmation source is invalid"
        )

    if (
        not isinstance(action_request_id, str)
        or not action_request_id.strip()
        or len(action_request_id.strip()) > 36
    ):
        raise ConversationPendingActionError(
            "Action request is invalid"
        )

    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        raise ConversationPendingActionError(
            "Trusted Church Space context is required"
        )

    required = {
        "event_id",
        "assignment_id",
        "status",
    }

    if (
        not isinstance(arguments, dict)
        or set(arguments) != required
    ):
        raise ConversationPendingActionError(
            "Service assignment status arguments are invalid"
        )

    for key in ("event_id", "assignment_id"):
        value = arguments.get(key)

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ConversationPendingActionError(
                "Service assignment status arguments are invalid"
            )

    status = arguments.get("status")

    if status not in {
        "assigned",
        "confirmed",
        "declined",
        "completed",
        "cancelled",
    }:
        raise ConversationPendingActionError(
            "Service assignment status arguments are invalid"
        )

    normalized_arguments = {
        "event_id": arguments["event_id"],
        "assignment_id": arguments["assignment_id"],
        "status": status,
    }

    conversation_id = conversation_id.strip()
    source_message_id = source_message_id.strip()
    action_request_id = action_request_id.strip()

    pending = (
        db.query(ConversationPendingAction)
        .filter(
            ConversationPendingAction.user_id == user_id
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
            action_name=(
                SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION
            ),
            resource_type=SERVICE_ASSIGNMENT_RESOURCE,
            resource_id=arguments["assignment_id"],
            source_message_id=source_message_id,
            arguments=normalized_arguments,
            action_request_id=action_request_id,
            church_id=church_id,
        )
        db.add(pending)
    else:
        pending.action_name = (
            SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION
        )
        pending.resource_type = SERVICE_ASSIGNMENT_RESOURCE
        pending.resource_id = arguments["assignment_id"]
        pending.source_message_id = source_message_id
        pending.arguments = normalized_arguments
        pending.action_request_id = action_request_id
        pending.church_id = church_id

    db.commit()
    return pending


def get_pending_service_assignment_status_update(
    *,
    db: Session,
    user_id: int,
    conversation_id: str,
    church_id: int,
) -> ConversationPendingAction | None:
    """
    Return only an exact pending assignment status transition.
    """
    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        return None

    if (
        not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or len(conversation_id.strip()) > 36
    ):
        return None

    pending = (
        db.query(ConversationPendingAction)
        .filter(
            ConversationPendingAction.user_id == user_id
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
        pending.church_id != church_id
        or pending.action_name
        != SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION
        or pending.resource_type
        != SERVICE_ASSIGNMENT_RESOURCE
        or not isinstance(pending.arguments, dict)
        or not pending.action_request_id
        or pending.resource_id
        != pending.arguments.get("assignment_id")
    ):
        return None

    return pending
