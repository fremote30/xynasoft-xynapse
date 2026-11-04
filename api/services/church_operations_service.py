"""Authoritative XynaFaith V2 Attendance and Service Operations service."""

from datetime import datetime

from sqlalchemy.orm import Session

from api.core.church_rbac import (
    MEMBERSHIP_STATUS_ACTIVE,
    PERMISSION_GROUPS_MANAGE,
)
from api.core.entitlements import (
    ENTITLEMENT_CHURCH_GROUPS,
    ENTITLEMENT_EVENTS,
)
from api.models.church_attendance import (
    ATTENDANCE_STATUSES,
    ATTENDANCE_STATUS_PRESENT,
    ChurchAttendanceRecord,
)
from api.models.church_event import ChurchEvent
from api.models.church_group import (
    GROUP_MEMBER_STATUS_ACTIVE,
    GROUP_STATUS_ACTIVE,
    GROUP_TYPE_TEAM,
    ChurchGroup,
    ChurchGroupMembership,
)
from api.models.church_membership import ChurchMembership
from api.models.church_service_assignment import (
    SERVICE_ASSIGNMENT_STATUSES,
    SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
    ChurchServiceAssignment,
)
from api.models.user import User
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    ChurchPermissionDenied,
    require_church_permission,
)
from api.services.effective_access_service import has_entitlement


class ChurchOperationsError(Exception):
    """Base Church Operations error."""


class ChurchOperationsNotFound(ChurchOperationsError):
    """Requested operational resource does not exist in this Church Space."""


class ChurchOperationsPermissionDenied(ChurchOperationsError):
    """Church Operations mutation is not authorized."""


class ChurchOperationsEntitlementRequired(ChurchOperationsError):
    """Church plan does not grant the requested operation."""


class ChurchOperationsValidationError(ChurchOperationsError):
    """Church Operations input is invalid."""


def _require_operations_management(
    db: Session,
    *,
    user: User,
    church_id: int,
) -> ChurchMembership:
    try:
        membership = require_church_permission(
            db,
            church_id=church_id,
            user_id=user.id,
            permission=PERMISSION_GROUPS_MANAGE,
        )
    except ChurchMembershipNotFound as exc:
        raise ChurchOperationsNotFound(
            "Church Space not found"
        ) from exc
    except ChurchMembershipInactive as exc:
        raise ChurchOperationsPermissionDenied(
            "Church membership is not active"
        ) from exc
    except ChurchPermissionDenied as exc:
        raise ChurchOperationsPermissionDenied(
            "Insufficient Church Space permission"
        ) from exc

    return membership


def _require_entitlement(
    db: Session,
    *,
    user: User,
    church_id: int,
    entitlement: str,
    message: str,
) -> None:
    if not has_entitlement(
        db,
        user,
        entitlement,
        church_id=church_id,
    ):
        raise ChurchOperationsEntitlementRequired(message)


def _get_event(
    db: Session,
    *,
    church_id: int,
    event_id: int,
) -> ChurchEvent:
    event = (
        db.query(ChurchEvent)
        .filter(
            ChurchEvent.id == event_id,
            ChurchEvent.church_id == church_id,
        )
        .one_or_none()
    )

    if event is None:
        raise ChurchOperationsNotFound("Event not found")

    return event


def _get_active_member(
    db: Session,
    *,
    church_id: int,
    church_membership_id: int,
) -> ChurchMembership:
    membership = (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.id == church_membership_id,
            ChurchMembership.church_id == church_id,
        )
        .one_or_none()
    )

    if membership is None:
        raise ChurchOperationsNotFound("Church member not found")

    if membership.status != MEMBERSHIP_STATUS_ACTIVE:
        raise ChurchOperationsValidationError(
            "Church member is not active"
        )

    return membership


def _get_team(
    db: Session,
    *,
    church_id: int,
    group_id: int,
) -> ChurchGroup:
    group = (
        db.query(ChurchGroup)
        .filter(
            ChurchGroup.id == group_id,
            ChurchGroup.church_id == church_id,
        )
        .one_or_none()
    )

    if group is None:
        raise ChurchOperationsNotFound("Service team not found")

    if group.status != GROUP_STATUS_ACTIVE:
        raise ChurchOperationsValidationError(
            "Service team is not active"
        )

    if group.group_type != GROUP_TYPE_TEAM:
        raise ChurchOperationsValidationError(
            "Service assignments require a team group"
        )

    return group


def record_attendance(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    church_membership_id: int,
    attendance_status: str = ATTENDANCE_STATUS_PRESENT,
    checked_in_at: datetime | None = None,
) -> ChurchAttendanceRecord:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    event = _get_event(
        db,
        church_id=church_id,
        event_id=event_id,
    )

    membership = _get_active_member(
        db,
        church_id=church_id,
        church_membership_id=church_membership_id,
    )

    normalized_status = attendance_status.strip()

    if normalized_status not in ATTENDANCE_STATUSES:
        raise ChurchOperationsValidationError(
            "Attendance status is invalid"
        )

    existing = (
        db.query(ChurchAttendanceRecord)
        .filter(
            ChurchAttendanceRecord.event_id == event.id,
            ChurchAttendanceRecord.church_membership_id
            == membership.id,
        )
        .one_or_none()
    )

    if existing is not None:
        raise ChurchOperationsValidationError(
            "Attendance has already been recorded for this member"
        )

    record = ChurchAttendanceRecord(
        event_id=event.id,
        church_membership_id=membership.id,
        status=normalized_status,
        recorded_by_user_id=user.id,
        checked_in_at=(
            checked_in_at
            if checked_in_at is not None
            else (
                datetime.utcnow()
                if normalized_status == ATTENDANCE_STATUS_PRESENT
                else None
            )
        ),
    )

    db.add(record)
    db.flush()

    return record


def list_event_attendance(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
) -> list[ChurchAttendanceRecord]:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    event = _get_event(
        db,
        church_id=church_id,
        event_id=event_id,
    )

    return (
        db.query(ChurchAttendanceRecord)
        .filter(
            ChurchAttendanceRecord.event_id == event.id,
        )
        .order_by(
            ChurchAttendanceRecord.church_membership_id.asc(),
            ChurchAttendanceRecord.id.asc(),
        )
        .all()
    )


def get_attendance_record(
    db: Session,
    *,
    church_id: int,
    event_id: int,
    attendance_id: int,
) -> ChurchAttendanceRecord:
    event = _get_event(
        db,
        church_id=church_id,
        event_id=event_id,
    )

    record = (
        db.query(ChurchAttendanceRecord)
        .filter(
            ChurchAttendanceRecord.id == attendance_id,
            ChurchAttendanceRecord.event_id == event.id,
        )
        .one_or_none()
    )

    if record is None:
        raise ChurchOperationsNotFound(
            "Attendance record not found"
        )

    return record


def update_attendance(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    attendance_id: int,
    attendance_status: str | None = None,
    checked_in_at: datetime | None = None,
    checked_in_at_provided: bool = False,
) -> ChurchAttendanceRecord:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    record = get_attendance_record(
        db,
        church_id=church_id,
        event_id=event_id,
        attendance_id=attendance_id,
    )

    if attendance_status is None and not checked_in_at_provided:
        raise ChurchOperationsValidationError(
            "At least one attendance field must be provided"
        )

    if attendance_status is not None:
        normalized_status = attendance_status.strip()

        if normalized_status not in ATTENDANCE_STATUSES:
            raise ChurchOperationsValidationError(
                "Attendance status is invalid"
            )

        record.status = normalized_status

    if checked_in_at_provided:
        record.checked_in_at = checked_in_at

    db.flush()

    return record


def list_member_attendance_history(
    db: Session,
    *,
    user: User,
    church_id: int,
    church_membership_id: int,
) -> list[ChurchAttendanceRecord]:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    membership = _get_active_member(
        db,
        church_id=church_id,
        church_membership_id=church_membership_id,
    )

    return (
        db.query(ChurchAttendanceRecord)
        .join(
            ChurchEvent,
            ChurchAttendanceRecord.event_id == ChurchEvent.id,
        )
        .filter(
            ChurchAttendanceRecord.church_membership_id
            == membership.id,
            ChurchEvent.church_id == church_id,
        )
        .order_by(
            ChurchEvent.starts_at.desc(),
            ChurchAttendanceRecord.id.desc(),
        )
        .all()
    )


def validate_service_assignment_for_user(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    group_id: int,
    church_membership_id: int,
    service_role: str,
):
    """
    Validate a proposed service assignment without mutating state.

    This is used before Xyniva asks for confirmation and again by
    the authoritative mutation path at execution time.
    """
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_CHURCH_GROUPS,
        message="Church Groups & Ministries are not available",
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    event = _get_event(
        db,
        church_id=church_id,
        event_id=event_id,
    )

    team = _get_team(
        db,
        church_id=church_id,
        group_id=group_id,
    )

    membership = _get_active_member(
        db,
        church_id=church_id,
        church_membership_id=church_membership_id,
    )

    active_team_membership = (
        db.query(ChurchGroupMembership)
        .filter(
            ChurchGroupMembership.group_id == team.id,
            ChurchGroupMembership.church_membership_id
            == membership.id,
            ChurchGroupMembership.status
            == GROUP_MEMBER_STATUS_ACTIVE,
        )
        .one_or_none()
    )

    if active_team_membership is None:
        raise ChurchOperationsValidationError(
            "Church member is not an active member of this service team"
        )

    normalized_role = service_role.strip()

    if not normalized_role or len(normalized_role) > 120:
        raise ChurchOperationsValidationError(
            "Service role is invalid"
        )

    existing = (
        db.query(ChurchServiceAssignment)
        .filter(
            ChurchServiceAssignment.event_id == event.id,
            ChurchServiceAssignment.group_id == team.id,
            ChurchServiceAssignment.church_membership_id
            == membership.id,
            ChurchServiceAssignment.service_role
            == normalized_role,
        )
        .one_or_none()
    )

    if existing is not None:
        raise ChurchOperationsValidationError(
            "This service assignment already exists"
        )

    return event, team, membership, normalized_role


def create_service_assignment(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    group_id: int,
    church_membership_id: int,
    service_role: str,
) -> ChurchServiceAssignment:
    (
        event,
        team,
        membership,
        normalized_role,
    ) = validate_service_assignment_for_user(
        db,
        user=user,
        church_id=church_id,
        event_id=event_id,
        group_id=group_id,
        church_membership_id=church_membership_id,
        service_role=service_role,
    )

    assignment = ChurchServiceAssignment(
        event_id=event.id,
        group_id=team.id,
        church_membership_id=membership.id,
        service_role=normalized_role,
        status="assigned",
        assigned_by_user_id=user.id,
    )

    db.add(assignment)
    db.flush()

    return assignment


def validate_service_assignment_reassignment_for_user(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    assignment_id: int,
    group_id: int,
    church_membership_id: int,
    service_role: str,
):
    """
    Validate a proposed service-assignment reassignment without
    mutating state.

    Reassignment preserves the original assignment as historical
    operational state and creates a replacement assignment only
    after explicit confirmation.
    """
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_CHURCH_GROUPS,
        message="Church Groups & Ministries are not available",
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    assignment = get_service_assignment(
        db,
        church_id=church_id,
        event_id=event_id,
        assignment_id=assignment_id,
    )

    if assignment.status not in {
        "assigned",
        "confirmed",
    }:
        raise ChurchOperationsValidationError(
            "Service assignment cannot be reassigned"
        )

    (
        event,
        team,
        membership,
        normalized_role,
    ) = validate_service_assignment_for_user(
        db,
        user=user,
        church_id=church_id,
        event_id=event_id,
        group_id=group_id,
        church_membership_id=church_membership_id,
        service_role=service_role,
    )

    if (
        assignment.group_id == team.id
        and assignment.church_membership_id == membership.id
        and assignment.service_role == normalized_role
    ):
        raise ChurchOperationsValidationError(
            "Service assignment replacement must be different"
        )

    return (
        assignment,
        event,
        team,
        membership,
        normalized_role,
    )


def reassign_service_assignment(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    assignment_id: int,
    group_id: int,
    church_membership_id: int,
    service_role: str,
) -> tuple[
    ChurchServiceAssignment,
    ChurchServiceAssignment,
]:
    """
    Cancel the original assignment and create its replacement.

    The caller owns the transaction. No commit occurs here so the
    original cancellation, replacement assignment, execution ledger,
    and pending-action consumption can become durable atomically.
    """
    (
        original_assignment,
        event,
        team,
        membership,
        normalized_role,
    ) = validate_service_assignment_reassignment_for_user(
        db,
        user=user,
        church_id=church_id,
        event_id=event_id,
        assignment_id=assignment_id,
        group_id=group_id,
        church_membership_id=church_membership_id,
        service_role=service_role,
    )

    original_assignment.status = (
        "cancelled"
    )

    replacement_assignment = ChurchServiceAssignment(
        event_id=event.id,
        group_id=team.id,
        church_membership_id=membership.id,
        service_role=normalized_role,
        status="assigned",
        assigned_by_user_id=user.id,
    )

    db.add(replacement_assignment)
    db.flush()

    return (
        original_assignment,
        replacement_assignment,
    )



def list_event_service_assignments(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
) -> list[ChurchServiceAssignment]:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_CHURCH_GROUPS,
        message="Church Groups & Ministries are not available",
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    event = _get_event(
        db,
        church_id=church_id,
        event_id=event_id,
    )

    return (
        db.query(ChurchServiceAssignment)
        .filter(
            ChurchServiceAssignment.event_id == event.id,
        )
        .order_by(
            ChurchServiceAssignment.group_id.asc(),
            ChurchServiceAssignment.service_role.asc(),
            ChurchServiceAssignment.id.asc(),
        )
        .all()
    )


def get_service_assignment(
    db: Session,
    *,
    church_id: int,
    event_id: int,
    assignment_id: int,
) -> ChurchServiceAssignment:
    event = _get_event(
        db,
        church_id=church_id,
        event_id=event_id,
    )

    assignment = (
        db.query(ChurchServiceAssignment)
        .filter(
            ChurchServiceAssignment.id == assignment_id,
            ChurchServiceAssignment.event_id == event.id,
        )
        .one_or_none()
    )

    if assignment is None:
        raise ChurchOperationsNotFound(
            "Service assignment not found"
        )

    return assignment


def validate_service_assignment_status_update_for_user(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    assignment_id: int,
    assignment_status: str,
) -> tuple[ChurchServiceAssignment, str]:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_CHURCH_GROUPS,
        message="Church Groups & Ministries are not available",
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_EVENTS,
        message="Church Events are not available",
    )

    assignment = get_service_assignment(
        db,
        church_id=church_id,
        event_id=event_id,
        assignment_id=assignment_id,
    )

    normalized_status = assignment_status.strip()

    if normalized_status not in SERVICE_ASSIGNMENT_STATUSES:
        raise ChurchOperationsValidationError(
            "Service assignment status is invalid"
        )

    allowed_transitions = {
        "assigned": {
            "confirmed",
            "declined",
            "cancelled",
        },
        "confirmed": {
            "completed",
            "cancelled",
        },
        "declined": set(),
        "completed": set(),
        "cancelled": set(),
    }

    if (
        normalized_status != assignment.status
        and normalized_status
        not in allowed_transitions.get(
            assignment.status,
            set(),
        )
    ):
        raise ChurchOperationsValidationError(
            "Service assignment status transition is invalid"
        )

    return assignment, normalized_status


def update_service_assignment(
    db: Session,
    *,
    user: User,
    church_id: int,
    event_id: int,
    assignment_id: int,
    assignment_status: str,
) -> ChurchServiceAssignment:
    assignment, normalized_status = (
        validate_service_assignment_status_update_for_user(
            db,
            user=user,
            church_id=church_id,
            event_id=event_id,
            assignment_id=assignment_id,
            assignment_status=assignment_status,
        )
    )

    if assignment.status == normalized_status:
        return assignment

    assignment.status = normalized_status
    db.flush()

    return assignment


def list_member_service_history(
    db: Session,
    *,
    user: User,
    church_id: int,
    church_membership_id: int,
) -> list[ChurchServiceAssignment]:
    _require_operations_management(
        db,
        user=user,
        church_id=church_id,
    )

    _require_entitlement(
        db,
        user=user,
        church_id=church_id,
        entitlement=ENTITLEMENT_CHURCH_GROUPS,
        message="Church Groups & Ministries are not available",
    )

    membership = _get_active_member(
        db,
        church_id=church_id,
        church_membership_id=church_membership_id,
    )

    return (
        db.query(ChurchServiceAssignment)
        .join(
            ChurchEvent,
            ChurchServiceAssignment.event_id == ChurchEvent.id,
        )
        .filter(
            ChurchServiceAssignment.church_membership_id
            == membership.id,
            ChurchEvent.church_id == church_id,
        )
        .order_by(
            ChurchEvent.starts_at.desc(),
            ChurchServiceAssignment.id.desc(),
        )
        .all()
    )
