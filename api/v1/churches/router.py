from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import (
    PERMISSION_CHURCH_VIEW,
    PERMISSION_CONTENT_CREATE,
    PERMISSION_CONTENT_MANAGE,
    PERMISSION_MEMBERS_VIEW,
    ROLE_PERMISSIONS,
)
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.church import Church
from api.models.church_announcement import (
    ANNOUNCEMENT_STATUSES,
    ANNOUNCEMENT_STATUS_DRAFT,
    ANNOUNCEMENT_STATUS_PUBLISHED,
    ChurchAnnouncement,
)
from api.models.church_event import (
    EVENT_STATUSES,
    EVENT_STATUS_DRAFT,
    EVENT_STATUS_PUBLISHED,
    ChurchEvent,
)
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.services.church_membership_service import get_primary_church_membership
from api.schemas.church_content import (
    AnnouncementCreate,
    AnnouncementUpdate,
    EventCreate,
    EventUpdate,
)


router = APIRouter(prefix="/churches", tags=["Church Spaces"])


church_view_required = require_church_permission_dependency(
    PERMISSION_CHURCH_VIEW
)

members_view_required = require_church_permission_dependency(
    PERMISSION_MEMBERS_VIEW
)


content_create_required = require_church_permission_dependency(
    PERMISSION_CONTENT_CREATE
)


def _permissions_for_membership(
    membership: ChurchMembership,
) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(membership.role, frozenset()))


def _church_payload(church: Church) -> dict:
    return {
        "id": church.id,
        "name": church.name,
        "location": church.location,
        "denomination": church.denomination,
        "country": church.country,
        "city": church.city,
        "is_featured": bool(church.is_featured),
        "is_verified": bool(church.is_verified),
    }


def _membership_payload(membership: ChurchMembership) -> dict:
    return {
        "id": membership.id,
        "church_id": membership.church_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "status": membership.status,
        "is_primary": bool(membership.is_primary),
        "joined_at": (
            membership.joined_at.isoformat()
            if membership.joined_at
            else None
        ),
    }


def _space_payload(
    church: Church,
    membership: ChurchMembership,
) -> dict:
    permissions = _permissions_for_membership(membership)

    return {
        "church": _church_payload(church),
        "membership": _membership_payload(membership),
        "permissions": permissions,
        "capabilities": {
            "can_manage_church": "church.manage" in permissions,
            "can_view_members": "members.view" in permissions,
            "can_manage_members": "members.manage" in permissions,
            "can_create_content": "content.create" in permissions,
            "can_manage_content": "content.manage" in permissions,
            "can_view_prayer": "prayer.view" in permissions,
            "can_manage_pastoral_care": (
                "pastoral_care.manage" in permissions
            ),
            "can_view_analytics": "analytics.view" in permissions,
        },
    }



def _announcement_payload(
    announcement: ChurchAnnouncement,
) -> dict:
    return {
        "id": announcement.id,
        "church_id": announcement.church_id,
        "author_user_id": announcement.author_user_id,
        "title": announcement.title,
        "body": announcement.body,
        "status": announcement.status,
        "published_at": (
            announcement.published_at.isoformat()
            if announcement.published_at
            else None
        ),
        "created_at": announcement.created_at.isoformat(),
        "updated_at": announcement.updated_at.isoformat(),
    }


def _event_payload(event: ChurchEvent) -> dict:
    return {
        "id": event.id,
        "church_id": event.church_id,
        "created_by_user_id": event.created_by_user_id,
        "title": event.title,
        "description": event.description,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": (
            event.ends_at.isoformat()
            if event.ends_at
            else None
        ),
        "location": event.location,
        "event_url": event.event_url,
        "status": event.status,
        "published_at": (
            event.published_at.isoformat()
            if event.published_at
            else None
        ),
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
    }


def _validate_event_dates(
    starts_at: datetime,
    ends_at: datetime | None,
) -> None:
    if ends_at is not None and ends_at < starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Event end time cannot be before start time",
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


@router.get("/mine")
def my_church_space(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = get_primary_church_membership(
        db,
        user_id=current_user.id,
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary Church Space found",
        )

    church = db.get(Church, membership.church_id)

    if church is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church Space not found",
        )

    return _space_payload(church, membership)


@router.get("/{church_id}/space")
def church_space(
    church_id: int,
    membership: ChurchMembership = Depends(church_view_required),
    db: Session = Depends(get_db),
):
    church = db.get(Church, church_id)

    if church is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church Space not found",
        )

    return _space_payload(church, membership)


@router.get("/{church_id}/members")
def church_members(
    church_id: int,
    _: ChurchMembership = Depends(members_view_required),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(ChurchMembership)
        .options(joinedload(ChurchMembership.user))
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.status == "active",
        )
        .order_by(
            ChurchMembership.is_primary.desc(),
            ChurchMembership.joined_at.asc(),
            ChurchMembership.id.asc(),
        )
        .all()
    )

    members = []

    for membership in memberships:
        user = membership.user

        members.append(
            {
                "membership_id": membership.id,
                "user_id": membership.user_id,
                "role": membership.role,
                "status": membership.status,
                "is_primary": bool(membership.is_primary),
                "joined_at": (
                    membership.joined_at.isoformat()
                    if membership.joined_at
                    else None
                ),
                "user": {
                    "id": user.id,
                    "name": getattr(user, "name", None),
                },
            }
        )

    return {
        "church_id": church_id,
        "members": members,
        "count": len(members),
    }


@router.get("/{church_id}/announcements")
def church_announcements(
    church_id: int,
    membership: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ChurchAnnouncement).filter(
        ChurchAnnouncement.church_id == church_id,
    )

    if not _has_content_manage(membership):
        query = query.filter(
            or_(
                ChurchAnnouncement.status
                == ANNOUNCEMENT_STATUS_PUBLISHED,
                (
                    (
                        ChurchAnnouncement.status
                        == ANNOUNCEMENT_STATUS_DRAFT
                    )
                    & (
                        ChurchAnnouncement.author_user_id
                        == current_user.id
                    )
                ),
            )
        )

    announcements = (
        query
        .order_by(
            ChurchAnnouncement.published_at.desc(),
            ChurchAnnouncement.created_at.desc(),
            ChurchAnnouncement.id.desc(),
        )
        .all()
    )

    return {
        "church_id": church_id,
        "announcements": [
            _announcement_payload(item)
            for item in announcements
        ],
        "count": len(announcements),
    }


@router.post(
    "/{church_id}/announcements",
    status_code=status.HTTP_201_CREATED,
)
def create_church_announcement(
    church_id: int,
    request: AnnouncementCreate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.status not in ANNOUNCEMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid announcement status",
        )

    if (
        request.status != ANNOUNCEMENT_STATUS_DRAFT
        and not _has_content_manage(membership)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Publishing requires content.manage",
        )

    announcement = ChurchAnnouncement(
        church_id=church_id,
        author_user_id=current_user.id,
        title=request.title.strip(),
        body=request.body.strip(),
        status=request.status,
        published_at=(
            datetime.utcnow()
            if request.status == ANNOUNCEMENT_STATUS_PUBLISHED
            else None
        ),
    )

    if not announcement.title or not announcement.body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Announcement title and body are required",
        )

    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    return _announcement_payload(announcement)


@router.patch("/{church_id}/announcements/{announcement_id}")
def update_church_announcement(
    church_id: int,
    announcement_id: int,
    request: AnnouncementUpdate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    announcement = (
        db.query(ChurchAnnouncement)
        .filter(
            ChurchAnnouncement.id == announcement_id,
            ChurchAnnouncement.church_id == church_id,
        )
        .one_or_none()
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found",
        )

    can_manage = _has_content_manage(membership)
    is_author = announcement.author_user_id == current_user.id

    if not can_manage:
        if (
            not is_author
            or announcement.status
            != ANNOUNCEMENT_STATUS_DRAFT
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission to edit announcement",
            )

    changes = request.model_dump(exclude_unset=True)

    if "status" in changes:
        new_status = changes["status"]

        if new_status not in ANNOUNCEMENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid announcement status",
            )

        if (
            new_status != ANNOUNCEMENT_STATUS_DRAFT
            and not can_manage
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Publishing or archiving requires content.manage",
            )

    if "title" in changes:
        title = changes["title"].strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Announcement title is required",
            )
        announcement.title = title

    if "body" in changes:
        body = changes["body"].strip()
        if not body:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Announcement body is required",
            )
        announcement.body = body

    if "status" in changes:
        announcement.status = changes["status"]

        if changes["status"] == ANNOUNCEMENT_STATUS_PUBLISHED:
            if announcement.published_at is None:
                announcement.published_at = datetime.utcnow()

    db.commit()
    db.refresh(announcement)

    return _announcement_payload(announcement)


@router.get("/{church_id}/events")
def church_events(
    church_id: int,
    membership: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ChurchEvent).filter(
        ChurchEvent.church_id == church_id,
    )

    if not _has_content_manage(membership):
        query = query.filter(
            or_(
                ChurchEvent.status
                == EVENT_STATUS_PUBLISHED,
                (
                    (
                        ChurchEvent.status
                        == EVENT_STATUS_DRAFT
                    )
                    & (
                        ChurchEvent.created_by_user_id
                        == current_user.id
                    )
                ),
            )
        )

    events = (
        query
        .order_by(
            ChurchEvent.starts_at.asc(),
            ChurchEvent.id.asc(),
        )
        .all()
    )

    return {
        "church_id": church_id,
        "events": [
            _event_payload(item)
            for item in events
        ],
        "count": len(events),
    }


@router.post(
    "/{church_id}/events",
    status_code=status.HTTP_201_CREATED,
)
def create_church_event(
    church_id: int,
    request: EventCreate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.status not in EVENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid event status",
        )

    if (
        request.status != EVENT_STATUS_DRAFT
        and not _has_content_manage(membership)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Publishing requires content.manage",
        )

    _validate_event_dates(
        request.starts_at,
        request.ends_at,
    )

    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Event title is required",
        )

    event = ChurchEvent(
        church_id=church_id,
        created_by_user_id=current_user.id,
        title=title,
        description=(
            request.description.strip()
            if request.description
            else None
        ),
        starts_at=request.starts_at,
        ends_at=request.ends_at,
        location=(
            request.location.strip()
            if request.location
            else None
        ),
        event_url=(
            str(request.event_url)
            if request.event_url
            else None
        ),
        status=request.status,
        published_at=(
            datetime.utcnow()
            if request.status == EVENT_STATUS_PUBLISHED
            else None
        ),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return _event_payload(event)


@router.patch("/{church_id}/events/{event_id}")
def update_church_event(
    church_id: int,
    event_id: int,
    request: EventUpdate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = (
        db.query(ChurchEvent)
        .filter(
            ChurchEvent.id == event_id,
            ChurchEvent.church_id == church_id,
        )
        .one_or_none()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    can_manage = _has_content_manage(membership)
    is_creator = event.created_by_user_id == current_user.id

    if not can_manage:
        if not is_creator or event.status != EVENT_STATUS_DRAFT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission to edit event",
            )

    changes = request.model_dump(exclude_unset=True)

    if "status" in changes:
        new_status = changes["status"]

        if new_status not in EVENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid event status",
            )

        if new_status != EVENT_STATUS_DRAFT and not can_manage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Publishing or cancelling requires content.manage",
            )

    next_start = changes.get(
        "starts_at",
        event.starts_at,
    )
    next_end = changes.get(
        "ends_at",
        event.ends_at,
    )

    _validate_event_dates(
        next_start,
        next_end,
    )

    if "title" in changes:
        title = changes["title"].strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Event title is required",
            )
        event.title = title

    for field in (
        "description",
        "starts_at",
        "ends_at",
        "location",
    ):
        if field in changes:
            value = changes[field]

            if field in {"description", "location"} and value:
                value = value.strip()

            setattr(event, field, value)

    if "event_url" in changes:
        event.event_url = (
            str(changes["event_url"])
            if changes["event_url"]
            else None
        )

    if "status" in changes:
        event.status = changes["status"]

        if changes["status"] == EVENT_STATUS_PUBLISHED:
            if event.published_at is None:
                event.published_at = datetime.utcnow()

    db.commit()
    db.refresh(event)

    return _event_payload(event)
