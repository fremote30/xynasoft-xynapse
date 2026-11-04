from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import (
    PERMISSION_CONTENT_MANAGE,
    PERMISSION_PASTORAL_CARE_MANAGE,
    PERMISSION_PRAYER_VIEW,
    ROLE_PERMISSIONS,
)
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.church_membership import ChurchMembership
from api.models.pastoral_care_activity import (
    PASTORAL_CARE_ACTIVITY_TYPES,
    PastoralCareActivity,
)
from api.models.pastoral_care_case import (
    PASTORAL_CARE_PRIORITIES,
    PASTORAL_CARE_STATUSES,
    PastoralCareCase,
)
from api.models.pastoral_care_note import PastoralCareNote
from api.models.prayer import Prayer, PrayerRecipient
from api.models.user import User
from api.schemas.church_prayer_care import (
    ChurchPrayerCreate,
    ChurchPrayerStatusUpdate,
    PastoralCareCaseUpdate,
    PastoralCareNoteCreate,
    TestimonyModerationUpdate,
)


router = APIRouter()

prayer_view_required = require_church_permission_dependency(
    PERMISSION_PRAYER_VIEW
)

pastoral_care_required = require_church_permission_dependency(
    PERMISSION_PASTORAL_CARE_MANAGE
)

content_manage_required = require_church_permission_dependency(
    PERMISSION_CONTENT_MANAGE
)

PRAYER_STATUSES = {
    "still_praying",
    "partially_answered",
    "answered",
}

PRAYER_VISIBILITIES = {
    "community",
    "private",
    "mixed",
}


def _has_permission(
    membership: ChurchMembership,
    permission: str,
) -> bool:
    return permission in ROLE_PERMISSIONS.get(
        membership.role,
        frozenset(),
    )


def _prayer_payload(
    prayer: Prayer,
    *,
    viewer_user_id: int | None = None,
    privileged: bool = False,
) -> dict:
    reveal_identity = (
        not prayer.is_anonymous
        or privileged
        or prayer.user_id == viewer_user_id
    )

    return {
        "id": prayer.id,
        "church_id": prayer.church_id,
        "user_id": (
            prayer.user_id
            if reveal_identity
            else None
        ),
        "user_name": (
            prayer.user_name
            if reveal_identity
            else "Anonymous"
        ),
        "message": prayer.message,
        "category": prayer.category,
        "visibility": prayer.visibility,
        "status": prayer.status,
        "is_anonymous": bool(prayer.is_anonymous),
        "pastoral_care_requested": bool(
            prayer.pastoral_care_requested
        ),
        "prayer_count": prayer.prayer_count,
        "support_count": prayer.support_count,
        "comment_count": prayer.comment_count,
        "share_count": prayer.share_count,
        "answered_at": (
            prayer.answered_at.isoformat()
            if prayer.answered_at
            else None
        ),
        "answer_testimony": prayer.answer_testimony,
        "testimony_status": prayer.testimony_status,
        "testimony_shared_at": (
            prayer.testimony_shared_at.isoformat()
            if prayer.testimony_shared_at
            else None
        ),
        "created_at": prayer.created_at.isoformat(),
        "updated_at": prayer.updated_at.isoformat(),
    }


def _case_payload(case: PastoralCareCase) -> dict:
    return {
        "id": case.id,
        "church_id": case.church_id,
        "prayer_id": case.prayer_id,
        "member_user_id": case.member_user_id,
        "assigned_to_user_id": case.assigned_to_user_id,
        "status": case.status,
        "priority": case.priority,
        "follow_up_at": (
            case.follow_up_at.isoformat()
            if case.follow_up_at
            else None
        ),
        "closed_at": (
            case.closed_at.isoformat()
            if case.closed_at
            else None
        ),
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
    }


def _note_payload(note: PastoralCareNote) -> dict:
    return {
        "id": note.id,
        "case_id": note.case_id,
        "church_id": note.church_id,
        "author_user_id": note.author_user_id,
        "body": note.body,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _activity_payload(activity: PastoralCareActivity) -> dict:
    return {
        "id": activity.id,
        "case_id": activity.case_id,
        "church_id": activity.church_id,
        "actor_user_id": activity.actor_user_id,
        "activity_type": activity.activity_type,
        "created_at": activity.created_at.isoformat(),
    }


def _activity(
    db: Session,
    *,
    case: PastoralCareCase,
    actor_user_id: int,
    activity_type: str,
) -> None:
    if activity_type not in PASTORAL_CARE_ACTIVITY_TYPES:
        raise ValueError("Invalid pastoral-care activity type")

    db.add(
        PastoralCareActivity(
            case_id=case.id,
            church_id=case.church_id,
            actor_user_id=actor_user_id,
            activity_type=activity_type,
        )
    )


def _recipient_ids(
    db: Session,
    *,
    prayer_id: int,
) -> set[int]:
    return {
        row[0]
        for row in (
            db.query(PrayerRecipient.recipient_user_id)
            .filter(PrayerRecipient.prayer_id == prayer_id)
            .all()
        )
    }


def _can_view_prayer(
    db: Session,
    *,
    prayer: Prayer,
    membership: ChurchMembership,
    current_user: User,
) -> bool:
    if prayer.user_id == current_user.id:
        return True

    # Preserve legacy-compatible semantics:
    # mixed remains community-visible while also having
    # explicitly selected recipients.
    if prayer.visibility in {"community", "mixed"}:
        return True

    if current_user.id in _recipient_ids(
        db,
        prayer_id=prayer.id,
    ):
        return True

    # Requesting pastoral care does not expose a private
    # prayer through the ordinary Prayer Wall. Authorized
    # care leaders access it through the care-case endpoint.
    return False


def _get_prayer(
    db: Session,
    *,
    church_id: int,
    prayer_id: int,
) -> Prayer:
    prayer = (
        db.query(Prayer)
        .filter(
            Prayer.id == prayer_id,
            Prayer.church_id == church_id,
        )
        .one_or_none()
    )

    if prayer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prayer not found",
        )

    return prayer


def _get_case(
    db: Session,
    *,
    church_id: int,
    case_id: int,
) -> PastoralCareCase:
    case = (
        db.query(PastoralCareCase)
        .filter(
            PastoralCareCase.id == case_id,
            PastoralCareCase.church_id == church_id,
        )
        .one_or_none()
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pastoral care case not found",
        )

    return case


def _validate_assignment(
    db: Session,
    *,
    church_id: int,
    user_id: int,
) -> None:
    membership = (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.user_id == user_id,
            ChurchMembership.status == "active",
        )
        .one_or_none()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assignee must be an active member of this Church Space",
        )

    if not _has_permission(
        membership,
        PERMISSION_PASTORAL_CARE_MANAGE,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assignee must have pastoral_care.manage permission",
        )


@router.get("/{church_id}/prayers")
def church_prayers(
    church_id: int,
    membership: ChurchMembership = Depends(prayer_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Prayer).filter(
        Prayer.church_id == church_id,
        Prayer.is_hidden.is_(False),
    )

    can_manage_care = _has_permission(
        membership,
        PERMISSION_PASTORAL_CARE_MANAGE,
    )

    visible = [
        prayer
        for prayer in (
            query.order_by(
                Prayer.created_at.desc(),
                Prayer.id.desc(),
            ).all()
        )
        if _can_view_prayer(
            db,
            prayer=prayer,
            membership=membership,
            current_user=current_user,
        )
    ]

    return {
        "church_id": church_id,
        "prayers": [
            _prayer_payload(
                item,
                viewer_user_id=current_user.id,
            )
            for item in visible
        ],
        "count": len(visible),
        "can_manage_pastoral_care": can_manage_care,
    }


@router.post(
    "/{church_id}/prayers",
    status_code=status.HTTP_201_CREATED,
)
def create_church_prayer(
    church_id: int,
    request: ChurchPrayerCreate,
    _: ChurchMembership = Depends(prayer_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prayer message is required",
        )

    visibility = request.visibility.strip().lower()

    if visibility not in PRAYER_VISIBILITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid prayer visibility",
        )

    recipient_ids = set(request.recipient_user_ids)

    if current_user.id in recipient_ids:
        recipient_ids.remove(current_user.id)

    if visibility in {"private", "mixed"} and not recipient_ids:
        if not request.request_pastoral_care:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Private prayer requires a recipient or pastoral care request",
            )

    if recipient_ids:
        memberships = (
            db.query(ChurchMembership)
            .filter(
                ChurchMembership.church_id == church_id,
                ChurchMembership.user_id.in_(recipient_ids),
                ChurchMembership.status == "active",
            )
            .all()
        )

        valid_ids = {item.user_id for item in memberships}

        if valid_ids != recipient_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Prayer recipients must be active members of this Church Space",
            )

    prayer = Prayer(
        user_id=current_user.id,
        user_name=(
            getattr(current_user, "name", None)
            or getattr(current_user, "full_name", None)
            or "Member"
        ),
        church_id=church_id,
        message=message,
        category=(
            request.category.strip()
            if request.category
            else None
        ),
        visibility=visibility,
        is_anonymous=request.is_anonymous,
        pastoral_care_requested=request.request_pastoral_care,
    )

    try:
        db.add(prayer)
        db.flush()

        for recipient_user_id in sorted(recipient_ids):
            db.add(
                PrayerRecipient(
                    prayer_id=prayer.id,
                    recipient_user_id=recipient_user_id,
                    recipient_role="member",
                )
            )

        case = None

        if request.request_pastoral_care:
            case = PastoralCareCase(
                church_id=church_id,
                prayer_id=prayer.id,
                member_user_id=current_user.id,
                status="open",
                priority="routine",
            )
            db.add(case)
            db.flush()

            _activity(
                db,
                case=case,
                actor_user_id=current_user.id,
                activity_type="case_created",
            )

        db.commit()
        db.refresh(prayer)

        if case is not None:
            db.refresh(case)

    except Exception:
        db.rollback()
        raise

    result = _prayer_payload(
        prayer,
        viewer_user_id=current_user.id,
    )
    result["pastoral_care_case"] = (
        _case_payload(case)
        if case is not None
        else None
    )
    return result


@router.get("/{church_id}/prayers/{prayer_id}")
def church_prayer_detail(
    church_id: int,
    prayer_id: int,
    membership: ChurchMembership = Depends(prayer_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prayer = _get_prayer(
        db,
        church_id=church_id,
        prayer_id=prayer_id,
    )

    if not _can_view_prayer(
        db,
        prayer=prayer,
        membership=membership,
        current_user=current_user,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prayer not found",
        )

    return _prayer_payload(
        prayer,
        viewer_user_id=current_user.id,
    )


@router.patch("/{church_id}/prayers/{prayer_id}/status")
def update_church_prayer_status(
    church_id: int,
    prayer_id: int,
    request: ChurchPrayerStatusUpdate,
    _: ChurchMembership = Depends(prayer_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prayer = _get_prayer(
        db,
        church_id=church_id,
        prayer_id=prayer_id,
    )

    if prayer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prayer not found",
        )

    new_status = request.status.strip().lower()

    if new_status not in PRAYER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid prayer status",
        )

    prayer.status = new_status

    if new_status == "answered":
        if prayer.answered_at is None:
            prayer.answered_at = datetime.utcnow()

        testimony = (
            request.answer_testimony.strip()
            if request.answer_testimony
            else None
        )
        prayer.answer_testimony = testimony

        # Member consent submits the testimony for review.
        # It does not publish directly to the Testimony Wall.
        prayer.testimony_status = (
            "pending"
            if testimony and request.share_testimony
            else None
        )
        prayer.testimony_shared_at = None
    else:
        prayer.answered_at = None
        prayer.answer_testimony = None
        prayer.testimony_status = None
        prayer.testimony_shared_at = None

    db.commit()
    db.refresh(prayer)

    return _prayer_payload(
        prayer,
        viewer_user_id=current_user.id,
    )


@router.get("/{church_id}/pastoral-care")
def pastoral_care_cases(
    church_id: int,
    _: ChurchMembership = Depends(pastoral_care_required),
    db: Session = Depends(get_db),
):
    cases = (
        db.query(PastoralCareCase)
        .filter(PastoralCareCase.church_id == church_id)
        .order_by(
            PastoralCareCase.created_at.desc(),
            PastoralCareCase.id.desc(),
        )
        .all()
    )

    return {
        "church_id": church_id,
        "cases": [_case_payload(item) for item in cases],
        "count": len(cases),
    }


@router.get("/{church_id}/pastoral-care/{case_id}")
def pastoral_care_case_detail(
    church_id: int,
    case_id: int,
    _: ChurchMembership = Depends(pastoral_care_required),
    db: Session = Depends(get_db),
):
    case = _get_case(
        db,
        church_id=church_id,
        case_id=case_id,
    )

    prayer = _get_prayer(
        db,
        church_id=church_id,
        prayer_id=case.prayer_id,
    )

    notes = (
        db.query(PastoralCareNote)
        .filter(
            PastoralCareNote.church_id == church_id,
            PastoralCareNote.case_id == case.id,
        )
        .order_by(
            PastoralCareNote.created_at.asc(),
            PastoralCareNote.id.asc(),
        )
        .all()
    )

    activities = (
        db.query(PastoralCareActivity)
        .filter(
            PastoralCareActivity.church_id == church_id,
            PastoralCareActivity.case_id == case.id,
        )
        .order_by(
            PastoralCareActivity.created_at.asc(),
            PastoralCareActivity.id.asc(),
        )
        .all()
    )

    return {
        "case": _case_payload(case),
        "prayer": _prayer_payload(
            prayer,
            privileged=True,
        ),
        "notes": [_note_payload(item) for item in notes],
        "activities": [
            _activity_payload(item)
            for item in activities
        ],
    }


@router.patch("/{church_id}/pastoral-care/{case_id}")
def update_pastoral_care_case(
    church_id: int,
    case_id: int,
    request: PastoralCareCaseUpdate,
    _: ChurchMembership = Depends(pastoral_care_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    case = _get_case(
        db,
        church_id=church_id,
        case_id=case_id,
    )

    changes = request.model_dump(exclude_unset=True)

    if "status" in changes:
        new_status = changes["status"]

        if new_status not in PASTORAL_CARE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid pastoral care status",
            )

    if "priority" in changes:
        if changes["priority"] not in PASTORAL_CARE_PRIORITIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid pastoral care priority",
            )

    if (
        "assigned_to_user_id" in changes
        and changes["assigned_to_user_id"] is not None
    ):
        _validate_assignment(
            db,
            church_id=church_id,
            user_id=changes["assigned_to_user_id"],
        )

    old_assignee = case.assigned_to_user_id
    old_status = case.status
    old_follow_up = case.follow_up_at

    if "assigned_to_user_id" in changes:
        case.assigned_to_user_id = changes["assigned_to_user_id"]

    if "priority" in changes:
        case.priority = changes["priority"]

    if "follow_up_at" in changes:
        case.follow_up_at = changes["follow_up_at"]

    if "status" in changes:
        case.status = changes["status"]

        if case.status == "closed":
            case.closed_at = datetime.utcnow()
        else:
            case.closed_at = None

    if (
        "assigned_to_user_id" in changes
        and old_assignee != case.assigned_to_user_id
    ):
        _activity(
            db,
            case=case,
            actor_user_id=current_user.id,
            activity_type=(
                "assigned"
                if old_assignee is None
                else "reassigned"
            ),
        )

    if "status" in changes and old_status != case.status:
        activity_type = "status_changed"

        if case.status == "resolved":
            activity_type = "resolved"
        elif case.status == "closed":
            activity_type = "closed"

        _activity(
            db,
            case=case,
            actor_user_id=current_user.id,
            activity_type=activity_type,
        )

    if (
        "follow_up_at" in changes
        and old_follow_up != case.follow_up_at
        and case.follow_up_at is not None
    ):
        _activity(
            db,
            case=case,
            actor_user_id=current_user.id,
            activity_type="follow_up_scheduled",
        )

    db.commit()
    db.refresh(case)

    return _case_payload(case)


@router.post(
    "/{church_id}/pastoral-care/{case_id}/notes",
    status_code=status.HTTP_201_CREATED,
)
def create_pastoral_care_note(
    church_id: int,
    case_id: int,
    request: PastoralCareNoteCreate,
    _: ChurchMembership = Depends(pastoral_care_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    case = _get_case(
        db,
        church_id=church_id,
        case_id=case_id,
    )

    body = request.body.strip()

    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pastoral care note is required",
        )

    note = PastoralCareNote(
        case_id=case.id,
        church_id=church_id,
        author_user_id=current_user.id,
        body=body,
    )

    try:
        db.add(note)
        db.flush()

        _activity(
            db,
            case=case,
            actor_user_id=current_user.id,
            activity_type="note_added",
        )

        db.commit()
        db.refresh(note)

    except Exception:
        db.rollback()
        raise

    return _note_payload(note)


@router.get(
    "/{church_id}/pastoral-care-assignees",
)
def list_pastoral_care_assignees(
    church_id: int,
    membership: ChurchMembership = Depends(
        pastoral_care_required
    ),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.status == "active",
        )
        .order_by(ChurchMembership.id.asc())
        .all()
    )

    assignees = []

    for item in memberships:
        permissions = ROLE_PERMISSIONS.get(
            item.role,
            frozenset(),
        )

        if (
            PERMISSION_PASTORAL_CARE_MANAGE
            not in permissions
        ):
            continue

        user = (
            db.query(User)
            .filter(User.id == item.user_id)
            .first()
        )

        if not user:
            continue

        assignees.append(
            {
                "user_id": user.id,
                "name": (
                    getattr(user, "name", None)
                    or "Church Leader"
                ),
                "role": item.role,
            }
        )

    return {"assignees": assignees}


@router.get("/{church_id}/testimonies")
def church_testimonies(
    church_id: int,
    _: ChurchMembership = Depends(prayer_view_required),
    db: Session = Depends(get_db),
):
    prayers = (
        db.query(Prayer)
        .filter(
            Prayer.church_id == church_id,
            Prayer.status == "answered",
            Prayer.testimony_status == "approved",
            Prayer.testimony_shared_at.isnot(None),
            Prayer.answer_testimony.isnot(None),
            Prayer.is_hidden.is_(False),
        )
        .order_by(
            Prayer.testimony_shared_at.desc(),
            Prayer.id.desc(),
        )
        .all()
    )

    return {
        "church_id": church_id,
        "testimonies": [
            {
                "prayer_id": prayer.id,
                "user_name": (
                    "Anonymous"
                    if prayer.is_anonymous
                    else prayer.user_name
                ),
                "is_anonymous": bool(prayer.is_anonymous),
                "testimony": prayer.answer_testimony,
                "shared_at": (
                    prayer.testimony_shared_at.isoformat()
                    if prayer.testimony_shared_at
                    else None
                ),
            }
            for prayer in prayers
        ],
        "count": len(prayers),
    }


@router.get("/{church_id}/testimonies/pending")
def pending_church_testimonies(
    church_id: int,
    _: ChurchMembership = Depends(content_manage_required),
    db: Session = Depends(get_db),
):
    prayers = (
        db.query(Prayer)
        .filter(
            Prayer.church_id == church_id,
            Prayer.status == "answered",
            Prayer.testimony_status == "pending",
            Prayer.answer_testimony.isnot(None),
            Prayer.is_hidden.is_(False),
        )
        .order_by(
            Prayer.answered_at.asc(),
            Prayer.id.asc(),
        )
        .all()
    )

    return {
        "church_id": church_id,
        "testimonies": [
            {
                "prayer_id": prayer.id,
                "user_name": (
                    "Anonymous"
                    if prayer.is_anonymous
                    else prayer.user_name
                ),
                "is_anonymous": bool(prayer.is_anonymous),
                "testimony": prayer.answer_testimony,
                "submitted_at": (
                    prayer.answered_at.isoformat()
                    if prayer.answered_at
                    else None
                ),
            }
            for prayer in prayers
        ],
        "count": len(prayers),
    }


@router.patch(
    "/{church_id}/testimonies/{prayer_id}",
)
def moderate_church_testimony(
    church_id: int,
    prayer_id: int,
    request: TestimonyModerationUpdate,
    _: ChurchMembership = Depends(content_manage_required),
    db: Session = Depends(get_db),
):
    prayer = _get_prayer(
        db,
        church_id=church_id,
        prayer_id=prayer_id,
    )

    decision = request.status.strip().lower()

    if decision not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid testimony moderation status",
        )

    if (
        prayer.status != "answered"
        or prayer.testimony_status != "pending"
        or not prayer.answer_testimony
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending testimony not found",
        )

    prayer.testimony_status = decision
    prayer.testimony_shared_at = (
        datetime.utcnow()
        if decision == "approved"
        else None
    )

    db.commit()
    db.refresh(prayer)

    return {
        "prayer_id": prayer.id,
        "testimony_status": prayer.testimony_status,
        "testimony_shared_at": (
            prayer.testimony_shared_at.isoformat()
            if prayer.testimony_shared_at
            else None
        ),
    }
