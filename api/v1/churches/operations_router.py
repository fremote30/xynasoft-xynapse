"""XynaFaith V2 Attendance and Service Operations API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import PERMISSION_GROUPS_MANAGE
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.church_attendance import ChurchAttendanceRecord
from api.models.church_membership import ChurchMembership
from api.models.church_service_assignment import ChurchServiceAssignment
from api.models.user import User
from api.schemas.church_operations import (
    AttendanceCreate,
    AttendanceUpdate,
    ServiceAssignmentCreate,
    ServiceAssignmentUpdate,
)
from api.services.church_operations_service import (
    ChurchOperationsEntitlementRequired,
    ChurchOperationsNotFound,
    ChurchOperationsPermissionDenied,
    ChurchOperationsValidationError,
    create_service_assignment,
    list_event_attendance,
    list_event_service_assignments,
    list_member_attendance_history,
    list_member_service_history,
    record_attendance,
    update_attendance,
    update_service_assignment,
)


router = APIRouter()

operations_manage_required = require_church_permission_dependency(
    PERMISSION_GROUPS_MANAGE
)


def _attendance_payload(record: ChurchAttendanceRecord) -> dict:
    return {
        "id": record.id,
        "event_id": record.event_id,
        "church_membership_id": record.church_membership_id,
        "status": record.status,
        "recorded_by_user_id": record.recorded_by_user_id,
        "checked_in_at": (
            record.checked_in_at.isoformat()
            if record.checked_in_at
            else None
        ),
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _assignment_payload(assignment: ChurchServiceAssignment) -> dict:
    return {
        "id": assignment.id,
        "event_id": assignment.event_id,
        "group_id": assignment.group_id,
        "church_membership_id": assignment.church_membership_id,
        "service_role": assignment.service_role,
        "status": assignment.status,
        "assigned_by_user_id": assignment.assigned_by_user_id,
        "created_at": assignment.created_at.isoformat(),
        "updated_at": assignment.updated_at.isoformat(),
    }


def _raise_operation_error(exc: Exception) -> None:
    if isinstance(exc, ChurchOperationsNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        (
            ChurchOperationsPermissionDenied,
            ChurchOperationsEntitlementRequired,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if isinstance(exc, ChurchOperationsValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    raise exc


@router.post(
    "/{church_id}/events/{event_id}/attendance",
    status_code=status.HTTP_201_CREATED,
)
def create_attendance(
    church_id: int,
    event_id: int,
    payload: AttendanceCreate,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        record = record_attendance(
            db,
            user=current_user,
            church_id=church_id,
            event_id=event_id,
            church_membership_id=payload.church_membership_id,
            attendance_status=payload.status,
            checked_in_at=payload.checked_in_at,
        )
        db.commit()
        db.refresh(record)
        return _attendance_payload(record)

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        db.rollback()
        _raise_operation_error(exc)


@router.get(
    "/{church_id}/events/{event_id}/attendance",
)
def event_attendance(
    church_id: int,
    event_id: int,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        records = list_event_attendance(
            db,
            user=current_user,
            church_id=church_id,
            event_id=event_id,
        )

        return {
            "church_id": church_id,
            "event_id": event_id,
            "attendance": [
                _attendance_payload(record)
                for record in records
            ],
            "count": len(records),
        }

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        _raise_operation_error(exc)


@router.patch(
    "/{church_id}/events/{event_id}/attendance/{attendance_id}",
)
def patch_attendance(
    church_id: int,
    event_id: int,
    attendance_id: int,
    payload: AttendanceUpdate,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True)

    try:
        record = update_attendance(
            db,
            user=current_user,
            church_id=church_id,
            event_id=event_id,
            attendance_id=attendance_id,
            attendance_status=changes.get("status"),
            checked_in_at=changes.get("checked_in_at"),
            checked_in_at_provided="checked_in_at" in changes,
        )
        db.commit()
        db.refresh(record)
        return _attendance_payload(record)

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        db.rollback()
        _raise_operation_error(exc)


@router.get(
    "/{church_id}/members/{church_membership_id}/attendance",
)
def member_attendance_history(
    church_id: int,
    church_membership_id: int,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        records = list_member_attendance_history(
            db,
            user=current_user,
            church_id=church_id,
            church_membership_id=church_membership_id,
        )

        return {
            "church_id": church_id,
            "church_membership_id": church_membership_id,
            "attendance": [
                _attendance_payload(record)
                for record in records
            ],
            "count": len(records),
        }

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        _raise_operation_error(exc)


@router.post(
    "/{church_id}/events/{event_id}/service-assignments",
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    church_id: int,
    event_id: int,
    payload: ServiceAssignmentCreate,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        assignment = create_service_assignment(
            db,
            user=current_user,
            church_id=church_id,
            event_id=event_id,
            group_id=payload.group_id,
            church_membership_id=payload.church_membership_id,
            service_role=payload.service_role,
        )
        db.commit()
        db.refresh(assignment)
        return _assignment_payload(assignment)

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        db.rollback()
        _raise_operation_error(exc)


@router.get(
    "/{church_id}/events/{event_id}/service-assignments",
)
def event_service_assignments(
    church_id: int,
    event_id: int,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        assignments = list_event_service_assignments(
            db,
            user=current_user,
            church_id=church_id,
            event_id=event_id,
        )

        return {
            "church_id": church_id,
            "event_id": event_id,
            "assignments": [
                _assignment_payload(item)
                for item in assignments
            ],
            "count": len(assignments),
        }

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        _raise_operation_error(exc)


@router.patch(
    "/{church_id}/events/{event_id}/service-assignments/{assignment_id}",
)
def patch_service_assignment(
    church_id: int,
    event_id: int,
    assignment_id: int,
    payload: ServiceAssignmentUpdate,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        assignment = update_service_assignment(
            db,
            user=current_user,
            church_id=church_id,
            event_id=event_id,
            assignment_id=assignment_id,
            assignment_status=payload.status,
        )
        db.commit()
        db.refresh(assignment)
        return _assignment_payload(assignment)

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        db.rollback()
        _raise_operation_error(exc)


@router.get(
    "/{church_id}/members/{church_membership_id}/service-history",
)
def member_service_history(
    church_id: int,
    church_membership_id: int,
    _membership: ChurchMembership = Depends(operations_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        assignments = list_member_service_history(
            db,
            user=current_user,
            church_id=church_id,
            church_membership_id=church_membership_id,
        )

        return {
            "church_id": church_id,
            "church_membership_id": church_membership_id,
            "assignments": [
                _assignment_payload(item)
                for item in assignments
            ],
            "count": len(assignments),
        }

    except (
        ChurchOperationsNotFound,
        ChurchOperationsPermissionDenied,
        ChurchOperationsEntitlementRequired,
        ChurchOperationsValidationError,
    ) as exc:
        _raise_operation_error(exc)
