"""Security and behavior tests for XynaFaith V2 Church Intelligence."""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.core.church_rbac import (
    CHURCH_ROLE_MEMBER,
    CHURCH_ROLE_PASTOR,
    MEMBERSHIP_STATUS_ACTIVE,
)
from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.church import Church
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
    GROUP_MEMBER_ROLE_MEMBER,
    GROUP_MEMBER_STATUS_ACTIVE,
    GROUP_STATUS_ACTIVE,
    GROUP_TYPE_MINISTRY,
    GROUP_TYPE_SMALL_GROUP,
    GROUP_TYPE_TEAM,
    ChurchGroup,
    ChurchGroupMembership,
)
from api.models.church_attendance import (
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
from api.models.reading_plan import (
    READING_PLAN_STATUS_PUBLISHED,
    ReadingPlan,
)
from api.models.user import User
from api.v1.churches.router import router


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine,
        tables=[
            Church.__table__,
            User.__table__,
            ChurchMembership.__table__,
            ChurchGroup.__table__,
            ChurchGroupMembership.__table__,
            ChurchAnnouncement.__table__,
            ChurchEvent.__table__,
            ChurchAttendanceRecord.__table__,
            ChurchServiceAssignment.__table__,
            ReadingPlan.__table__,
            Prayer.__table__,
            PastoralCareCase.__table__,
        ],
    )

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def app(db, monkeypatch):
    # Route/RBAC tests isolate the commercial entitlement boundary.
    monkeypatch.setattr(
        "api.v1.churches.intelligence_router.has_entitlement",
        lambda db, user, entitlement_key, church_id=None: True,
    )

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    state = {"user": None}

    def override_db():
        yield db

    def override_user():
        return state["user"]

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_current_user] = override_user
    test_app.state.auth = state

    yield test_app

    test_app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


def create_church(db, name):
    church = Church(
        name=name,
        location="Accra",
        country="Ghana",
        city="Accra",
    )
    db.add(church)
    db.flush()
    return church


def create_user(db, name, *, role="member"):
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '-')}@example.test",
        password="not-a-real-password",
        role=role,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def create_membership(db, *, church, user, role):
    membership = ChurchMembership(
        church_id=church.id,
        user_id=user.id,
        role=role,
        status=MEMBERSHIP_STATUS_ACTIVE,
        is_primary=False,
    )
    db.add(membership)
    db.flush()
    return membership


def create_prayer(db, *, church, user, message="Please pray"):
    prayer = Prayer(
        user_id=user.id,
        user_name=user.name,
        church_id=church.id,
        message=message,
        visibility="community",
        status="still_praying",
        is_anonymous=False,
        pastoral_care_requested=False,
    )
    db.add(prayer)
    db.flush()
    return prayer


def authenticate(app, user):
    app.state.auth["user"] = user


def test_pastor_receives_deterministic_church_intelligence(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Grace Pastor", role="pastor")
    member = create_user(db, "Grace Member")

    pastor_membership = create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )

    db.add(
        ChurchAnnouncement(
            church_id=church.id,
            author_user_id=pastor.id,
            title="Sunday Service",
            body="Service begins at 9 AM.",
            status=ANNOUNCEMENT_STATUS_PUBLISHED,
            published_at=datetime.utcnow(),
        )
    )

    event = ChurchEvent(
        church_id=church.id,
        created_by_user_id=pastor.id,
        title="Prayer Night",
        starts_at=datetime.utcnow() + timedelta(days=2),
        status=EVENT_STATUS_PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db.add(event)
    db.flush()

    recent_attendance_event = ChurchEvent(
        church_id=church.id,
        created_by_user_id=pastor.id,
        title="Recent Sunday Service",
        starts_at=datetime.utcnow() - timedelta(days=7),
        status=EVENT_STATUS_PUBLISHED,
        published_at=datetime.utcnow() - timedelta(days=8),
    )
    db.add(recent_attendance_event)
    db.flush()

    old_attendance_event = ChurchEvent(
        church_id=church.id,
        created_by_user_id=pastor.id,
        title="Old Sunday Service",
        starts_at=datetime.utcnow() - timedelta(days=45),
        status=EVENT_STATUS_PUBLISHED,
        published_at=datetime.utcnow() - timedelta(days=46),
    )
    db.add(old_attendance_event)
    db.flush()

    ministry_group = ChurchGroup(
        church_id=church.id,
        name="Prayer Ministry",
        group_type=GROUP_TYPE_MINISTRY,
        status=GROUP_STATUS_ACTIVE,
    )
    small_group = ChurchGroup(
        church_id=church.id,
        name="Young Adults",
        group_type=GROUP_TYPE_SMALL_GROUP,
        status=GROUP_STATUS_ACTIVE,
    )
    service_team = ChurchGroup(
        church_id=church.id,
        name="Welcome Team",
        group_type=GROUP_TYPE_TEAM,
        status=GROUP_STATUS_ACTIVE,
    )

    db.add_all(
        [
            ministry_group,
            small_group,
            service_team,
        ]
    )
    db.flush()

    db.add_all(
        [
            ChurchGroupMembership(
                group_id=ministry_group.id,
                church_membership_id=pastor_membership.id,
                role=GROUP_MEMBER_ROLE_MEMBER,
                status=GROUP_MEMBER_STATUS_ACTIVE,
            ),
            ChurchGroupMembership(
                group_id=small_group.id,
                church_membership_id=member_membership.id,
                role=GROUP_MEMBER_ROLE_MEMBER,
                status=GROUP_MEMBER_STATUS_ACTIVE,
            ),
            ChurchGroupMembership(
                group_id=service_team.id,
                church_membership_id=member_membership.id,
                role=GROUP_MEMBER_ROLE_MEMBER,
                status=GROUP_MEMBER_STATUS_ACTIVE,
            ),
        ]
    )

    db.add(
        ChurchAttendanceRecord(
            event_id=recent_attendance_event.id,
            church_membership_id=member_membership.id,
            status=ATTENDANCE_STATUS_PRESENT,
            recorded_by_user_id=pastor.id,
            checked_in_at=datetime.utcnow() - timedelta(days=7),
        )
    )

    # Historical attendance outside the 30-day intelligence window must
    # not affect the current operational summary.
    db.add(
        ChurchAttendanceRecord(
            event_id=old_attendance_event.id,
            church_membership_id=member_membership.id,
            status=ATTENDANCE_STATUS_PRESENT,
            recorded_by_user_id=pastor.id,
            checked_in_at=datetime.utcnow() - timedelta(days=45),
        )
    )

    db.add_all(
        [
            ChurchServiceAssignment(
                event_id=event.id,
                group_id=service_team.id,
                church_membership_id=member_membership.id,
                service_role="Greeter",
                status=SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
                assigned_by_user_id=pastor.id,
            ),
            ChurchServiceAssignment(
                event_id=event.id,
                group_id=service_team.id,
                church_membership_id=pastor_membership.id,
                service_role="Team Lead",
                status=SERVICE_ASSIGNMENT_STATUS_CONFIRMED,
                assigned_by_user_id=pastor.id,
            ),
        ]
    )

    db.add(
        ReadingPlan(
            church_id=church.id,
            creator_user_id=pastor.id,
            title="Faith Journey",
            description="A church reading plan.",
            duration_days=7,
            status=READING_PLAN_STATUS_PUBLISHED,
        )
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        message="Please pray for my family",
    )

    db.add(
        PastoralCareCase(
            church_id=church.id,
            prayer_id=prayer.id,
            member_user_id=member.id,
            status="open",
            priority="urgent",
            follow_up_at=datetime.utcnow() - timedelta(days=1),
        )
    )

    db.commit()
    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{church.id}/intelligence/summary"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["church_id"] == church.id

    assert payload["members"]["active"] == 2
    assert payload["members"]["roles"]["pastor"] == 1
    assert payload["members"]["roles"]["member"] == 1

    assert payload["ministry"]["published_announcements"] == 1
    assert payload["ministry"]["upcoming_events"] == 1
    assert payload["ministry"]["published_reading_plans"] == 1
    assert payload["ministry"]["prayers"] == 1

    assert payload["groups"] == {
        "active": 3,
        "ministries": 1,
        "small_groups": 1,
        "service_teams": 1,
        "active_memberships": 3,
    }

    assert payload["operations"] == {
        "attendance_records": 1,
        "present": 1,
        "absent": 0,
        "excused": 0,
        "upcoming_service_assignments": 2,
        "confirmed_service_assignments": 1,
        "unconfirmed_service_assignments": 1,
    }

    assert payload["pastoral_care"]["active_cases"] == 1
    assert payload["pastoral_care"]["urgent_cases"] == 1
    assert payload["pastoral_care"]["overdue_follow_ups"] == 1
    assert payload["pastoral_care"]["upcoming_follow_ups"] == 0
    assert payload["pastoral_care"]["unassigned_cases"] == 1

    assert payload["signals"] == {
        "urgent_care_present": True,
        "overdue_follow_up_present": True,
        "unassigned_care_present": True,
        "upcoming_events_present": True,
        "active_service_teams_present": True,
        "service_confirmation_needed": True,
    }


def test_member_cannot_view_church_intelligence(
    client,
    app,
    db,
):
    church = create_church(db, "Member Church")
    member = create_user(db, "Ordinary Member")

    create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )

    db.commit()
    authenticate(app, member)

    response = client.get(
        f"/api/v1/churches/{church.id}/intelligence/summary"
    )

    assert response.status_code == 403


def test_foreign_church_intelligence_is_hidden(
    client,
    app,
    db,
):
    own_church = create_church(db, "Own Church")
    foreign_church = create_church(db, "Foreign Church")
    pastor = create_user(db, "Tenant Pastor", role="pastor")

    create_membership(
        db,
        church=own_church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    db.commit()
    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{foreign_church.id}/intelligence/summary"
    )

    assert response.status_code == 404


def test_foreign_church_data_does_not_affect_summary(
    client,
    app,
    db,
):
    church = create_church(db, "Primary Church")
    foreign_church = create_church(db, "Foreign Data Church")

    pastor = create_user(db, "Primary Pastor", role="pastor")
    foreign_member = create_user(db, "Foreign Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    create_membership(
        db,
        church=foreign_church,
        user=foreign_member,
        role=CHURCH_ROLE_MEMBER,
    )

    foreign_prayer = create_prayer(
        db,
        church=foreign_church,
        user=foreign_member,
    )

    db.add(
        PastoralCareCase(
            church_id=foreign_church.id,
            prayer_id=foreign_prayer.id,
            member_user_id=foreign_member.id,
            status="open",
            priority="urgent",
            follow_up_at=datetime.utcnow() - timedelta(days=3),
        )
    )

    db.commit()
    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{church.id}/intelligence/summary"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["members"]["active"] == 1
    assert payload["ministry"]["prayers"] == 0
    assert payload["pastoral_care"]["active_cases"] == 0
    assert payload["pastoral_care"]["urgent_cases"] == 0
    assert payload["pastoral_care"]["overdue_follow_ups"] == 0


def test_missing_church_intelligence_entitlement_returns_403(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Unsubscribed Church")
    pastor = create_user(db, "Unsubscribed Pastor", role="pastor")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    monkeypatch.setattr(
        "api.v1.churches.intelligence_router.has_entitlement",
        lambda db, user, entitlement_key, church_id=None: False,
    )

    db.commit()
    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{church.id}/intelligence/summary"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Church Intelligence is not available"
    )
