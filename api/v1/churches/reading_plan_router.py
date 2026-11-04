from datetime import datetime

"""
XynaFaith V2 Church Space reading-plan authoring.

Church RBAC controls who may author/manage content.
Product entitlements control whether Reading Plans are available.

Lifecycle operations such as publishing are intentionally kept separate
from ordinary draft editing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import (
    PERMISSION_CONTENT_CREATE,
    PERMISSION_CONTENT_MANAGE,
    ROLE_PERMISSIONS,
)
from api.core.dependencies import get_current_user
from api.core.entitlements import ENTITLEMENT_READING_PLANS
from api.db.database import get_db
from api.models.church_membership import ChurchMembership
from api.models.reading_plan import (
    READING_PLAN_STATUS_ARCHIVED,
    READING_PLAN_STATUS_DRAFT,
    READING_PLAN_STATUS_PUBLISHED,
    ReadingPlan,
    ReadingPlanDay,
)
from api.models.user import User
from api.schemas.reading_plan_authoring import (
    ReadingPlanCreate,
    ReadingPlanDayCreate,
    ReadingPlanDayUpdate,
    ReadingPlanUpdate,
)
from api.services.effective_access_service import has_entitlement


router = APIRouter(
    prefix="/{church_id}/reading-plans",
    tags=["Church Reading Plans"],
)


content_create_required = require_church_permission_dependency(
    PERMISSION_CONTENT_CREATE
)

content_manage_required = require_church_permission_dependency(
    PERMISSION_CONTENT_MANAGE
)


def _has_content_manage(
    membership: ChurchMembership,
) -> bool:
    return (
        PERMISSION_CONTENT_MANAGE
        in ROLE_PERMISSIONS.get(
            membership.role,
            frozenset(),
        )
    )


def _require_reading_plans_entitlement(
    db: Session,
    user: User,
    church_id: int,
) -> None:
    if not has_entitlement(
        db,
        user,
        ENTITLEMENT_READING_PLANS,
        church_id=church_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reading Plans are not available for this account",
        )


def _day_payload(day) -> dict:
    return {
        "id": day.id,
        "day_number": day.day_number,
        "title": day.title,
        "scripture": day.scripture,
        "reflection": day.reflection,
        "prompt": day.prompt,
    }


def _plan_payload(plan: ReadingPlan) -> dict:
    return {
        "id": plan.id,
        "church_id": plan.church_id,
        "creator_user_id": plan.creator_user_id,
        "title": plan.title,
        "description": plan.description,
        "duration_days": plan.duration_days,
        "status": plan.status,
        "published_at": (
            plan.published_at.isoformat()
            if plan.published_at
            else None
        ),
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
        "days": [
            _day_payload(day)
            for day in plan.days
        ],
    }


def _get_church_plan(
    db: Session,
    *,
    church_id: int,
    plan_id: int,
) -> ReadingPlan:
    plan = (
        db.query(ReadingPlan)
        .options(selectinload(ReadingPlan.days))
        .filter(
            ReadingPlan.id == plan_id,
            ReadingPlan.church_id == church_id,
        )
        .one_or_none()
    )

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading Plan not found",
        )

    return plan


def _require_editable_plan(
    plan: ReadingPlan,
    *,
    membership: ChurchMembership,
    current_user: User,
) -> None:
    if _has_content_manage(membership):
        return

    if (
        plan.creator_user_id != current_user.id
        or plan.status != READING_PLAN_STATUS_DRAFT
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission to edit Reading Plan",
        )


def _validate_plan_for_publish(
    plan: ReadingPlan,
) -> None:
    days = sorted(
        plan.days,
        key=lambda day: day.day_number,
    )

    if not days:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Reading Plan must contain at least one day "
                "before publishing"
            ),
        )

    actual_day_numbers = [
        day.day_number
        for day in days
    ]
    expected_day_numbers = list(
        range(1, len(days) + 1)
    )

    if actual_day_numbers != expected_day_numbers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Reading Plan days must be sequential "
                "from 1 through the final day before publishing"
            ),
        )

    for day in days:
        if not day.scripture or not day.scripture.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Reading Plan day {day.day_number} "
                    "must contain scripture before publishing"
                ),
            )


def _require_draft_structure(
    plan: ReadingPlan,
) -> None:
    if plan.status != READING_PLAN_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Reading Plan day structure can only be changed "
                "while the plan is draft"
            ),
        )


def _get_plan_day(
    db: Session,
    *,
    plan_id: int,
    day_id: int,
) -> ReadingPlanDay:
    day = (
        db.query(ReadingPlanDay)
        .filter(
            ReadingPlanDay.id == day_id,
            ReadingPlanDay.plan_id == plan_id,
        )
        .one_or_none()
    )

    if day is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading Plan day not found",
        )

    return day


def _require_unique_day_number(
    db: Session,
    *,
    plan_id: int,
    day_number: int,
    exclude_day_id: int | None = None,
) -> None:
    query = db.query(ReadingPlanDay).filter(
        ReadingPlanDay.plan_id == plan_id,
        ReadingPlanDay.day_number == day_number,
    )

    if exclude_day_id is not None:
        query = query.filter(
            ReadingPlanDay.id != exclude_day_id
        )

    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Reading Plan already contains day {day_number}"
            ),
        )


def _sync_duration_days(
    db: Session,
    plan: ReadingPlan,
) -> None:
    plan.duration_days = (
        db.query(ReadingPlanDay)
        .filter(ReadingPlanDay.plan_id == plan.id)
        .count()
    )


@router.get("")
def list_church_reading_plans(
    church_id: int,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    query = (
        db.query(ReadingPlan)
        .options(selectinload(ReadingPlan.days))
        .filter(ReadingPlan.church_id == church_id)
    )

    if not _has_content_manage(membership):
        query = query.filter(
            or_(
                ReadingPlan.status == READING_PLAN_STATUS_PUBLISHED,
                (
                    (ReadingPlan.status == READING_PLAN_STATUS_DRAFT)
                    & (
                        ReadingPlan.creator_user_id
                        == current_user.id
                    )
                ),
            )
        )

    plans = (
        query
        .order_by(
            ReadingPlan.updated_at.desc(),
            ReadingPlan.id.desc(),
        )
        .all()
    )

    return {
        "church_id": church_id,
        "reading_plans": [
            _plan_payload(plan)
            for plan in plans
        ],
        "count": len(plans),
    }


@router.get("/{plan_id}")
def get_church_reading_plan(
    church_id: int,
    plan_id: int,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    if not _has_content_manage(membership):
        visible = (
            plan.status == READING_PLAN_STATUS_PUBLISHED
            or (
                plan.status == READING_PLAN_STATUS_DRAFT
                and plan.creator_user_id == current_user.id
            )
        )

        if not visible:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reading Plan not found",
            )

    return _plan_payload(plan)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_church_reading_plan(
    church_id: int,
    request: ReadingPlanCreate,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reading Plan title is required",
        )

    description = (
        request.description.strip()
        if request.description
        else None
    )

    plan = ReadingPlan(
        church_id=church_id,
        creator_user_id=current_user.id,
        title=title,
        description=description or None,
        duration_days=0,
        status=READING_PLAN_STATUS_DRAFT,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return _plan_payload(plan)


@router.patch("/{plan_id}")
def update_church_reading_plan(
    church_id: int,
    plan_id: int,
    request: ReadingPlanUpdate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    _require_editable_plan(
        plan,
        membership=membership,
        current_user=current_user,
    )

    changes = request.model_dump(exclude_unset=True)

    # Lifecycle changes are not ordinary draft edits. Publishing and
    # archiving will use dedicated validated operations.
    if "status" in changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Reading Plan status cannot be changed "
                "through this endpoint"
            ),
        )

    if "title" in changes:
        title = changes["title"]

        if title is None or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Reading Plan title is required",
            )

        plan.title = title.strip()

    if "description" in changes:
        description = changes["description"]

        plan.description = (
            description.strip()
            if description and description.strip()
            else None
        )

    db.commit()
    db.refresh(plan)

    return _plan_payload(plan)

@router.post(
    "/{plan_id}/days",
    status_code=status.HTTP_201_CREATED,
)
def create_reading_plan_day(
    church_id: int,
    plan_id: int,
    request: ReadingPlanDayCreate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    _require_editable_plan(
        plan,
        membership=membership,
        current_user=current_user,
    )
    _require_draft_structure(plan)

    _require_unique_day_number(
        db,
        plan_id=plan.id,
        day_number=request.day_number,
    )

    scripture = request.scripture.strip()

    if not scripture:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scripture is required",
        )

    day = ReadingPlanDay(
        plan_id=plan.id,
        day_number=request.day_number,
        title=(
            request.title.strip()
            if request.title and request.title.strip()
            else None
        ),
        scripture=scripture,
        reflection=(
            request.reflection.strip()
            if request.reflection and request.reflection.strip()
            else None
        ),
        prompt=(
            request.prompt.strip()
            if request.prompt and request.prompt.strip()
            else None
        ),
    )

    db.add(day)
    db.flush()

    _sync_duration_days(db, plan)

    db.commit()
    db.refresh(day)

    return _day_payload(day)


@router.patch(
    "/{plan_id}/days/{day_id}",
)
def update_reading_plan_day(
    church_id: int,
    plan_id: int,
    day_id: int,
    request: ReadingPlanDayUpdate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    _require_editable_plan(
        plan,
        membership=membership,
        current_user=current_user,
    )
    _require_draft_structure(plan)

    day = _get_plan_day(
        db,
        plan_id=plan.id,
        day_id=day_id,
    )

    changes = request.model_dump(exclude_unset=True)

    if "day_number" in changes:
        day_number = changes["day_number"]

        if day_number is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Day number is required",
            )

        _require_unique_day_number(
            db,
            plan_id=plan.id,
            day_number=day_number,
            exclude_day_id=day.id,
        )
        day.day_number = day_number

    if "title" in changes:
        title = changes["title"]
        day.title = (
            title.strip()
            if title and title.strip()
            else None
        )

    if "scripture" in changes:
        scripture = changes["scripture"]

        if scripture is None or not scripture.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Scripture is required",
            )

        day.scripture = scripture.strip()

    if "reflection" in changes:
        reflection = changes["reflection"]
        day.reflection = (
            reflection.strip()
            if reflection and reflection.strip()
            else None
        )

    if "prompt" in changes:
        prompt = changes["prompt"]
        day.prompt = (
            prompt.strip()
            if prompt and prompt.strip()
            else None
        )

    db.commit()
    db.refresh(day)

    return _day_payload(day)


@router.delete(
    "/{plan_id}/days/{day_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reading_plan_day(
    church_id: int,
    plan_id: int,
    day_id: int,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    _require_editable_plan(
        plan,
        membership=membership,
        current_user=current_user,
    )
    _require_draft_structure(plan)

    day = _get_plan_day(
        db,
        plan_id=plan.id,
        day_id=day_id,
    )

    db.delete(day)
    db.flush()

    _sync_duration_days(db, plan)

    db.commit()

    return None

@router.post(
    "/{plan_id}/publish",
)
def publish_reading_plan(
    church_id: int,
    plan_id: int,
    _: ChurchMembership = Depends(content_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    if plan.status != READING_PLAN_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft Reading Plans can be published",
        )

    _validate_plan_for_publish(plan)

    plan.duration_days = len(plan.days)
    plan.status = READING_PLAN_STATUS_PUBLISHED
    plan.published_at = datetime.utcnow()

    db.commit()
    db.refresh(plan)

    return _plan_payload(plan)


@router.post(
    "/{plan_id}/archive",
)
def archive_reading_plan(
    church_id: int,
    plan_id: int,
    _: ChurchMembership = Depends(content_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_reading_plans_entitlement(
        db,
        current_user,
        church_id,
    )

    plan = _get_church_plan(
        db,
        church_id=church_id,
        plan_id=plan_id,
    )

    if plan.status != READING_PLAN_STATUS_PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only published Reading Plans can be archived",
        )

    plan.status = READING_PLAN_STATUS_ARCHIVED

    db.commit()
    db.refresh(plan)

    return _plan_payload(plan)
