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
from api.models.user import User
from api.services.church_announcement_service import (
    ChurchAnnouncementActionError,
    build_announcement_draft_for_user,
)
from api.services.church_event_service import (
    ChurchEventActionError,
    build_event_draft_for_user,
)
from api.services.church_operations_service import (
    ChurchOperationsError,
    create_service_assignment,
    reassign_service_assignment,
    update_service_assignment,
)
from api.services.sermon_persistence import (
    SermonNotFoundError,
    build_sermon_delete_for_user,
    build_sermon_for_user,
    build_sermon_update_for_user,
)


ANNOUNCEMENT_SAVE_DRAFT_ACTION = "announcement.save_draft"
EVENT_SAVE_DRAFT_ACTION = "event.save_draft"
SERVICE_ASSIGNMENT_CREATE_ACTION = "service_assignment.create"
SERVICE_ASSIGNMENT_REASSIGN_ACTION = (
    "service_assignment.reassign"
)
SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION = (
    "service_assignment.update_status"
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
    current_user: User | None = None,
    church_id: int | None = None,
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
        ANNOUNCEMENT_SAVE_DRAFT_ACTION,
        EVENT_SAVE_DRAFT_ACTION,
        SERVICE_ASSIGNMENT_CREATE_ACTION,
        SERVICE_ASSIGNMENT_REASSIGN_ACTION,
        SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION,
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

    if not isinstance(arguments, dict):
        raise ConversationActionContextError(
            "Conversation action arguments are invalid"
        )

    if action_name == SERVICE_ASSIGNMENT_CREATE_ACTION:
        required_assignment_fields = {
            "event_id",
            "group_id",
            "church_membership_id",
            "service_role",
        }

        if set(arguments) != required_assignment_fields:
            raise ConversationActionContextError(
                "service_assignment.create requires exact "
                "service assignment arguments"
            )

        for field in (
            "event_id",
            "group_id",
            "church_membership_id",
        ):
            value = arguments.get(field)

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise ConversationActionContextError(
                    "Service assignment identifiers are invalid"
                )

        service_role = arguments.get("service_role")

        if (
            not isinstance(service_role, str)
            or not service_role.strip()
            or len(service_role.strip()) > 120
        ):
            raise ConversationActionContextError(
                "Service assignment role is invalid"
            )

        if current_user is None or current_user.id != user_id:
            raise ConversationActionContextError(
                "Authenticated user context is required"
            )

        if (
            not isinstance(church_id, int)
            or isinstance(church_id, bool)
            or church_id < 1
        ):
            raise ConversationActionContextError(
                "Trusted Church Space context is required"
            )

    if action_name == SERVICE_ASSIGNMENT_REASSIGN_ACTION:
        required_reassignment_fields = {
            "event_id",
            "assignment_id",
            "group_id",
            "church_membership_id",
            "service_role",
        }

        if set(arguments) != required_reassignment_fields:
            raise ConversationActionContextError(
                "service_assignment.reassign requires exact "
                "reassignment arguments"
            )

        for field in (
            "event_id",
            "assignment_id",
            "group_id",
            "church_membership_id",
        ):
            value = arguments.get(field)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise ConversationActionContextError(
                    "Service assignment identifiers are invalid"
                )

        service_role = arguments.get("service_role")
        if (
            not isinstance(service_role, str)
            or not service_role.strip()
            or len(service_role.strip()) > 120
        ):
            raise ConversationActionContextError(
                "Service assignment role is invalid"
            )

        arguments["service_role"] = service_role.strip()

        if current_user is None or current_user.id != user_id:
            raise ConversationActionContextError(
                "Authenticated user context is required"
            )

        if (
            not isinstance(church_id, int)
            or isinstance(church_id, bool)
            or church_id < 1
        ):
            raise ConversationActionContextError(
                "Trusted Church Space context is required"
            )

    if action_name == SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION:
        required_status_fields = {
            "event_id",
            "assignment_id",
            "status",
        }

        if set(arguments) != required_status_fields:
            raise ConversationActionContextError(
                "service_assignment.update_status requires exact "
                "status update arguments"
            )

        for field in ("event_id", "assignment_id"):
            value = arguments.get(field)

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise ConversationActionContextError(
                    "Service assignment identifiers are invalid"
                )

        if arguments.get("status") not in {
            "confirmed",
            "declined",
            "completed",
            "cancelled",
        }:
            raise ConversationActionContextError(
                "Service assignment status is invalid"
            )

        if current_user is None or current_user.id != user_id:
            raise ConversationActionContextError(
                "Authenticated user context is required"
            )

        if (
            not isinstance(church_id, int)
            or isinstance(church_id, bool)
            or church_id < 1
        ):
            raise ConversationActionContextError(
                "Trusted Church Space context is required"
            )

    if (
        action_name in {
            SERMON_SAVE_ACTION,
            SERMON_UPDATE_ACTION,
            SERMON_DELETE_ACTION,
        }
        and arguments
    ):
        raise ConversationActionContextError(
            f"{action_name} does not accept arguments"
        )

    if action_name == ANNOUNCEMENT_SAVE_DRAFT_ACTION:
        if set(arguments) != {"title", "body"}:
            raise ConversationActionContextError(
                "announcement.save_draft accepts only title and body"
            )

        title = arguments.get("title")
        body = arguments.get("body")

        if not isinstance(title, str) or not isinstance(body, str):
            raise ConversationActionContextError(
                "Announcement title and body are required"
            )

        if current_user is None or current_user.id != user_id:
            raise ConversationActionContextError(
                "Authenticated user context is required"
            )

        if (
            not isinstance(church_id, int)
            or isinstance(church_id, bool)
            or church_id < 1
        ):
            raise ConversationActionContextError(
                "Trusted Church Space context is required"
            )

    if action_name == EVENT_SAVE_DRAFT_ACTION:
        allowed_event_fields = {
            "title",
            "description",
            "starts_at",
            "ends_at",
            "location",
            "event_url",
        }

        if not set(arguments).issubset(allowed_event_fields):
            raise ConversationActionContextError(
                "event.save_draft accepts only event content fields"
            )

        if "title" not in arguments or "starts_at" not in arguments:
            raise ConversationActionContextError(
                "Event title and start time are required"
            )

        if current_user is None or current_user.id != user_id:
            raise ConversationActionContextError(
                "Authenticated user context is required"
            )

        if (
            not isinstance(church_id, int)
            or isinstance(church_id, bool)
            or church_id < 1
        ):
            raise ConversationActionContextError(
                "Trusted Church Space context is required"
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

    if action_name == SERVICE_ASSIGNMENT_CREATE_ACTION:
        if (
            pending_action is None
            or pending_action.user_id != user_id
            or pending_action.action_name
            != SERVICE_ASSIGNMENT_CREATE_ACTION
            or pending_action.resource_type
            != "service_assignment"
            or pending_action.resource_id
            != arguments["event_id"]
            or pending_action.church_id != church_id
            or pending_action.arguments != arguments
            or not pending_action.action_request_id
            or pending_action.action_request_id
            != request_id
        ):
            raise ConversationActionContextError(
                "service_assignment.create requires trusted "
                "pending confirmation"
            )

    if action_name == SERVICE_ASSIGNMENT_REASSIGN_ACTION:
        if (
            pending_action is None
            or pending_action.user_id != user_id
            or pending_action.action_name
            != SERVICE_ASSIGNMENT_REASSIGN_ACTION
            or pending_action.resource_type
            != "service_assignment"
            or pending_action.resource_id
            != arguments["assignment_id"]
            or pending_action.church_id != church_id
            or pending_action.arguments != arguments
            or not pending_action.action_request_id
            or pending_action.action_request_id
            != request_id
        ):
            raise ConversationActionContextError(
                "service_assignment.reassign requires trusted "
                "pending confirmation"
            )

    if action_name == SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION:
        if (
            pending_action is None
            or pending_action.user_id != user_id
            or pending_action.action_name
            != SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION
            or pending_action.resource_type
            != "service_assignment"
            or pending_action.resource_id
            != arguments["assignment_id"]
            or pending_action.church_id != church_id
            or pending_action.arguments != arguments
            or not pending_action.action_request_id
            or pending_action.action_request_id
            != request_id
        ):
            raise ConversationActionContextError(
                "service_assignment.update_status requires trusted "
                "pending confirmation"
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

    if action_name == ANNOUNCEMENT_SAVE_DRAFT_ACTION:
        try:
            announcement = build_announcement_draft_for_user(
                db=db,
                user=current_user,
                church_id=church_id,
                title=title,
                body=body,
            )
        except ChurchAnnouncementActionError as exc:
            raise ConversationActionContextError(
                str(exc)
            ) from exc

        result_payload = {
            "announcement_id": announcement.id,
            "church_id": announcement.church_id,
            "status": announcement.status,
        }

    elif action_name == EVENT_SAVE_DRAFT_ACTION:
        try:
            event = build_event_draft_for_user(
                db=db,
                user=current_user,
                church_id=church_id,
                event_data=arguments,
            )
        except ChurchEventActionError as exc:
            raise ConversationActionContextError(
                str(exc)
            ) from exc

        result_payload = {
            "event_id": event.id,
            "church_id": event.church_id,
            "status": event.status,
        }

    elif action_name == SERVICE_ASSIGNMENT_CREATE_ACTION:
        try:
            assignment = create_service_assignment(
                db=db,
                user=current_user,
                church_id=church_id,
                event_id=arguments["event_id"],
                group_id=arguments["group_id"],
                church_membership_id=arguments[
                    "church_membership_id"
                ],
                service_role=arguments["service_role"],
            )
        except ChurchOperationsError as exc:
            raise ConversationActionContextError(
                str(exc)
            ) from exc

        result_payload = {
            "assignment_id": assignment.id,
            "church_id": church_id,
            "event_id": assignment.event_id,
            "group_id": assignment.group_id,
            "church_membership_id":
                assignment.church_membership_id,
            "service_role": assignment.service_role,
            "status": assignment.status,
        }

    elif action_name == SERVICE_ASSIGNMENT_REASSIGN_ACTION:
        try:
            original, replacement = reassign_service_assignment(
                db,
                user=current_user,
                church_id=church_id,
                event_id=arguments["event_id"],
                assignment_id=arguments["assignment_id"],
                group_id=arguments["group_id"],
                church_membership_id=arguments[
                    "church_membership_id"
                ],
                service_role=arguments["service_role"],
            )
        except ChurchOperationsError as exc:
            raise ConversationActionContextError(
                str(exc)
            ) from exc

        result_payload = {
            "original_assignment_id": original.id,
            "original_status": original.status,
            "replacement_assignment_id": replacement.id,
            "church_id": church_id,
            "event_id": replacement.event_id,
            "group_id": replacement.group_id,
            "church_membership_id": (
                replacement.church_membership_id
            ),
            "service_role": replacement.service_role,
            "status": replacement.status,
        }

    elif action_name == SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION:
        try:
            assignment = update_service_assignment(
                db,
                user=current_user,
                church_id=church_id,
                event_id=arguments["event_id"],
                assignment_id=arguments["assignment_id"],
                assignment_status=arguments["status"],
            )
        except ChurchOperationsError as exc:
            raise ConversationActionContextError(
                str(exc)
            ) from exc

        result_payload = {
            "assignment_id": assignment.id,
            "church_id": assignment.church_id,
            "event_id": assignment.event_id,
            "group_id": assignment.group_id,
            "church_membership_id": (
                assignment.church_membership_id
            ),
            "service_role": assignment.service_role,
            "status": assignment.status,
        }

    elif action_name == SERMON_SAVE_ACTION:
        sermon = build_sermon_for_user(
            db=db,
            user_id=user_id,
            payload=sermon_data,
        )
        result_payload = {
            "sermon_id": sermon.id,
        }
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

        result_payload = {
            "sermon_id": sermon.id,
        }
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

    if action_name == SERMON_DELETE_ACTION:
        result_payload = {
            "sermon_id": sermon.id,
        }

    execution = ConversationActionExecution(
        user_id=user_id,
        request_id=request_id,
        source_message_id=source_message_id,
        action_name=action_name,
        status="completed",
        result=result_payload,
    )

    db.add(execution)

    if action_name in {
        SERMON_DELETE_ACTION,
        SERVICE_ASSIGNMENT_CREATE_ACTION,
        SERVICE_ASSIGNMENT_REASSIGN_ACTION,
        SERVICE_ASSIGNMENT_UPDATE_STATUS_ACTION,
    }:
        db.delete(pending_action)

    try:
        # Product mutation, execution record, and any consumed
        # destructive confirmation become durable together.
        db.commit()

    except IntegrityError:
        # A concurrent request may have completed the same
        # action first. Roll back our product mutation and load
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
