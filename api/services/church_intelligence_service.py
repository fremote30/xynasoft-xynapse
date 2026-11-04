"""Deterministic Church Intelligence for XynaFaith V2.

This service derives church-scoped operational facts from authoritative
XynaFaith data. It does not call an LLM and does not expose private
pastoral-care note contents.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.church_announcement import (
    ANNOUNCEMENT_STATUS_PUBLISHED,
    ChurchAnnouncement,
)
from api.models.church_event import (
    EVENT_STATUS_PUBLISHED,
    ChurchEvent,
)
from api.models.church_membership import ChurchMembership
from api.models.church_group import (
    GROUP_MEMBER_STATUS_ACTIVE,
    GROUP_STATUS_ACTIVE,
    GROUP_TYPE_MINISTRY,
    GROUP_TYPE_SMALL_GROUP,
    GROUP_TYPE_TEAM,
    ChurchGroup,
    ChurchGroupMembership,
)
from api.models.church_attendance import (
    ATTENDANCE_STATUS_ABSENT,
    ATTENDANCE_STATUS_EXCUSED,
    ATTENDANCE_STATUS_PRESENT,
    ChurchAttendanceRecord,
)
from api.models.church_service_assignment import (
    SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
    SERVICE_ASSIGNMENT_STATUS_CONFIRMED,
    ChurchServiceAssignment,
)
from api.models.pastoral_care_case import PastoralCareCase
from api.models.prayer import Prayer
from api.models.reading_plan import ReadingPlan


ACTIVE_MEMBERSHIP_STATUS = "active"
ACTIVE_CARE_STATUSES = (
    "open",
    "in_progress",
    "waiting",
)


def get_church_intelligence_summary(
    db: Session,
    *,
    church_id: int,
    now: datetime | None = None,
) -> dict:
    """Return deterministic operational intelligence for one Church Space."""

    now = now or datetime.utcnow()
    attendance_window_start = now - timedelta(days=30)

    active_members = (
        db.query(func.count(ChurchMembership.id))
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.status == ACTIVE_MEMBERSHIP_STATUS,
        )
        .scalar()
        or 0
    )

    role_rows = (
        db.query(
            ChurchMembership.role,
            func.count(ChurchMembership.id),
        )
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.status == ACTIVE_MEMBERSHIP_STATUS,
        )
        .group_by(ChurchMembership.role)
        .all()
    )

    role_distribution = {
        role: count
        for role, count in role_rows
    }

    published_announcements = (
        db.query(func.count(ChurchAnnouncement.id))
        .filter(
            ChurchAnnouncement.church_id == church_id,
            ChurchAnnouncement.status == ANNOUNCEMENT_STATUS_PUBLISHED,
        )
        .scalar()
        or 0
    )

    upcoming_events = (
        db.query(func.count(ChurchEvent.id))
        .filter(
            ChurchEvent.church_id == church_id,
            ChurchEvent.status == EVENT_STATUS_PUBLISHED,
            ChurchEvent.starts_at >= now,
        )
        .scalar()
        or 0
    )

    active_groups = (
        db.query(func.count(ChurchGroup.id))
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.status == GROUP_STATUS_ACTIVE,
        )
        .scalar()
        or 0
    )

    active_ministry_groups = (
        db.query(func.count(ChurchGroup.id))
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.status == GROUP_STATUS_ACTIVE,
            ChurchGroup.group_type == GROUP_TYPE_MINISTRY,
        )
        .scalar()
        or 0
    )

    active_small_groups = (
        db.query(func.count(ChurchGroup.id))
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.status == GROUP_STATUS_ACTIVE,
            ChurchGroup.group_type == GROUP_TYPE_SMALL_GROUP,
        )
        .scalar()
        or 0
    )

    active_service_teams = (
        db.query(func.count(ChurchGroup.id))
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.status == GROUP_STATUS_ACTIVE,
            ChurchGroup.group_type == GROUP_TYPE_TEAM,
        )
        .scalar()
        or 0
    )

    active_group_memberships = (
        db.query(func.count(ChurchGroupMembership.id))
        .join(
            ChurchGroup,
            ChurchGroup.id == ChurchGroupMembership.group_id,
        )
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.status == GROUP_STATUS_ACTIVE,
            ChurchGroupMembership.status == GROUP_MEMBER_STATUS_ACTIVE,
        )
        .scalar()
        or 0
    )

    attendance_rows = (
        db.query(
            ChurchAttendanceRecord.status,
            func.count(ChurchAttendanceRecord.id),
        )
        .join(
            ChurchEvent,
            ChurchEvent.id == ChurchAttendanceRecord.event_id,
        )
        .filter(
            ChurchEvent.church_id == church_id,
            ChurchEvent.status == EVENT_STATUS_PUBLISHED,
            ChurchEvent.starts_at >= attendance_window_start,
            ChurchEvent.starts_at < now,
        )
        .group_by(ChurchAttendanceRecord.status)
        .all()
    )

    attendance_counts = {
        status: count
        for status, count in attendance_rows
    }

    attendance_records = sum(attendance_counts.values())
    attendance_present = attendance_counts.get(
        ATTENDANCE_STATUS_PRESENT,
        0,
    )
    attendance_absent = attendance_counts.get(
        ATTENDANCE_STATUS_ABSENT,
        0,
    )
    attendance_excused = attendance_counts.get(
        ATTENDANCE_STATUS_EXCUSED,
        0,
    )

    upcoming_service_assignments = (
        db.query(func.count(ChurchServiceAssignment.id))
        .join(
            ChurchEvent,
            ChurchEvent.id == ChurchServiceAssignment.event_id,
        )
        .filter(
            ChurchEvent.church_id == church_id,
            ChurchEvent.status == EVENT_STATUS_PUBLISHED,
            ChurchEvent.starts_at >= now,
            ChurchServiceAssignment.status.in_(
                (
                    SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
                    SERVICE_ASSIGNMENT_STATUS_CONFIRMED,
                )
            ),
        )
        .scalar()
        or 0
    )

    confirmed_service_assignments = (
        db.query(func.count(ChurchServiceAssignment.id))
        .join(
            ChurchEvent,
            ChurchEvent.id == ChurchServiceAssignment.event_id,
        )
        .filter(
            ChurchEvent.church_id == church_id,
            ChurchEvent.status == EVENT_STATUS_PUBLISHED,
            ChurchEvent.starts_at >= now,
            ChurchServiceAssignment.status
            == SERVICE_ASSIGNMENT_STATUS_CONFIRMED,
        )
        .scalar()
        or 0
    )

    unconfirmed_service_assignments = (
        db.query(func.count(ChurchServiceAssignment.id))
        .join(
            ChurchEvent,
            ChurchEvent.id == ChurchServiceAssignment.event_id,
        )
        .filter(
            ChurchEvent.church_id == church_id,
            ChurchEvent.status == EVENT_STATUS_PUBLISHED,
            ChurchEvent.starts_at >= now,
            ChurchServiceAssignment.status
            == SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
        )
        .scalar()
        or 0
    )

    published_reading_plans = (
        db.query(func.count(ReadingPlan.id))
        .filter(
            ReadingPlan.church_id == church_id,
            ReadingPlan.status == "published",
        )
        .scalar()
        or 0
    )

    prayer_count = (
        db.query(func.count(Prayer.id))
        .filter(
            Prayer.church_id == church_id,
        )
        .scalar()
        or 0
    )

    active_care_base = db.query(PastoralCareCase).filter(
        PastoralCareCase.church_id == church_id,
        PastoralCareCase.status.in_(ACTIVE_CARE_STATUSES),
    )

    active_care_cases = active_care_base.count()

    urgent_care_cases = active_care_base.filter(
        PastoralCareCase.priority == "urgent",
    ).count()

    overdue_follow_ups = active_care_base.filter(
        PastoralCareCase.follow_up_at.isnot(None),
        PastoralCareCase.follow_up_at < now,
    ).count()

    upcoming_follow_ups = active_care_base.filter(
        PastoralCareCase.follow_up_at.isnot(None),
        PastoralCareCase.follow_up_at >= now,
    ).count()

    unassigned_care_cases = active_care_base.filter(
        PastoralCareCase.assigned_to_user_id.is_(None),
    ).count()

    return {
        "church_id": church_id,
        "generated_at": now.isoformat(),
        "members": {
            "active": active_members,
            "roles": role_distribution,
        },
        "ministry": {
            "published_announcements": published_announcements,
            "upcoming_events": upcoming_events,
            "published_reading_plans": published_reading_plans,
            "prayers": prayer_count,
        },
        "groups": {
            "active": active_groups,
            "ministries": active_ministry_groups,
            "small_groups": active_small_groups,
            "service_teams": active_service_teams,
            "active_memberships": active_group_memberships,
        },
        "operations": {
            "attendance_records": attendance_records,
            "present": attendance_present,
            "absent": attendance_absent,
            "excused": attendance_excused,
            "upcoming_service_assignments": upcoming_service_assignments,
            "confirmed_service_assignments": confirmed_service_assignments,
            "unconfirmed_service_assignments": unconfirmed_service_assignments,
        },
        "pastoral_care": {
            "active_cases": active_care_cases,
            "urgent_cases": urgent_care_cases,
            "overdue_follow_ups": overdue_follow_ups,
            "upcoming_follow_ups": upcoming_follow_ups,
            "unassigned_cases": unassigned_care_cases,
        },
        "signals": {
            "urgent_care_present": urgent_care_cases > 0,
            "overdue_follow_up_present": overdue_follow_ups > 0,
            "unassigned_care_present": unassigned_care_cases > 0,
            "upcoming_events_present": upcoming_events > 0,
            "active_service_teams_present": active_service_teams > 0,
            "service_confirmation_needed": (
                unconfirmed_service_assignments > 0
            ),
        },
    }
