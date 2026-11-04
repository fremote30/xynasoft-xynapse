"""
Security and behavior tests for XynaFaith V2 Church Space
announcements and basic events.

These tests use isolated in-memory SQLite and never connect
to the V1 or V2 PostgreSQL databases.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.core.church_rbac import (
    CHURCH_ROLE_ADMIN,
    CHURCH_ROLE_MEMBER,
    CHURCH_ROLE_MINISTRY_LEADER,
    CHURCH_ROLE_PASTOR,
    MEMBERSHIP_STATUS_ACTIVE,
)
from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.church import Church
from api.models.church_announcement import (
    ANNOUNCEMENT_STATUS_ARCHIVED,
    ANNOUNCEMENT_STATUS_DRAFT,
    ANNOUNCEMENT_STATUS_PUBLISHED,
    ChurchAnnouncement,
)
from api.models.church_event import (
    EVENT_STATUS_CANCELLED,
    EVENT_STATUS_DRAFT,
    EVENT_STATUS_PUBLISHED,
    ChurchEvent,
)
from api.models.church_membership import ChurchMembership
from api.models.church_group import (
    GROUP_MEMBER_STATUS_ACTIVE,
    GROUP_MEMBER_STATUS_INVITED,
    GROUP_MEMBER_STATUS_LEFT,
    GROUP_STATUS_ACTIVE,
    ChurchGroup,
    ChurchGroupMembership,
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
def app(db):
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


def create_church(db, name="Grace Church"):
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


def create_membership(
    db,
    *,
    church,
    user,
    role=CHURCH_ROLE_MEMBER,
):
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


def create_announcement(
    db,
    *,
    church,
    author,
    title,
    status=ANNOUNCEMENT_STATUS_DRAFT,
):
    item = ChurchAnnouncement(
        church_id=church.id,
        author_user_id=author.id,
        title=title,
        body=f"{title} body",
        status=status,
        published_at=(
            datetime.utcnow()
            if status == ANNOUNCEMENT_STATUS_PUBLISHED
            else None
        ),
    )
    db.add(item)
    db.flush()
    return item


def create_event(
    db,
    *,
    church,
    creator,
    title,
    status=EVENT_STATUS_DRAFT,
):
    item = ChurchEvent(
        church_id=church.id,
        created_by_user_id=creator.id,
        title=title,
        starts_at=datetime.utcnow() + timedelta(days=1),
        status=status,
        published_at=(
            datetime.utcnow()
            if status == EVENT_STATUS_PUBLISHED
            else None
        ),
    )
    db.add(item)
    db.flush()
    return item


def create_group(
    db,
    *,
    church,
    name,
):
    group = ChurchGroup(
        church_id=church.id,
        name=name,
        description=f"{name} description",
        group_type="ministry",
        status=GROUP_STATUS_ACTIVE,
    )
    db.add(group)
    db.flush()
    return group


def create_group_membership(
    db,
    *,
    group,
    church_membership,
    status=GROUP_MEMBER_STATUS_ACTIVE,
):
    item = ChurchGroupMembership(
        group_id=group.id,
        church_membership_id=church_membership.id,
        role="member",
        status=status,
    )
    db.add(item)
    db.flush()
    return item


def authenticate(app, user):
    app.state.auth["user"] = user


def test_member_sees_only_published_content(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Member")
    leader = create_user(db, "Leader")

    create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )

    create_announcement(
        db,
        church=church,
        author=leader,
        title="Published announcement",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )
    create_announcement(
        db,
        church=church,
        author=leader,
        title="Private draft",
    )

    create_event(
        db,
        church=church,
        creator=leader,
        title="Published event",
        status=EVENT_STATUS_PUBLISHED,
    )
    create_event(
        db,
        church=church,
        creator=leader,
        title="Private event draft",
    )

    db.commit()
    authenticate(app, member)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert [
        item["title"]
        for item in announcements.json()["announcements"]
    ] == ["Published announcement"]

    assert events.status_code == 200
    assert [
        item["title"]
        for item in events.json()["events"]
    ] == ["Published event"]


def test_creator_sees_published_and_own_drafts_only(
    client,
    app,
    db,
):
    church = create_church(db)
    leader = create_user(db, "Ministry Leader")
    other = create_user(db, "Other Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    create_announcement(
        db,
        church=church,
        author=leader,
        title="Own draft",
    )
    create_announcement(
        db,
        church=church,
        author=other,
        title="Other draft",
    )
    create_announcement(
        db,
        church=church,
        author=other,
        title="Published",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )

    create_event(
        db,
        church=church,
        creator=leader,
        title="Own event draft",
    )
    create_event(
        db,
        church=church,
        creator=other,
        title="Other event draft",
    )
    create_event(
        db,
        church=church,
        creator=other,
        title="Published event",
        status=EVENT_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, leader)

    announcement_response = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    event_response = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    announcement_titles = {
        item["title"]
        for item in announcement_response.json()["announcements"]
    }
    event_titles = {
        item["title"]
        for item in event_response.json()["events"]
    }

    assert announcement_titles == {
        "Own draft",
        "Published",
    }
    assert event_titles == {
        "Own event draft",
        "Published event",
    }


def test_manager_sees_all_church_content(
    client,
    app,
    db,
):
    church = create_church(db)
    pastor = create_user(db, "Pastor", role="pastor")
    author = create_user(db, "Author")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    create_announcement(
        db,
        church=church,
        author=author,
        title="Draft",
    )
    create_announcement(
        db,
        church=church,
        author=author,
        title="Published",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )

    create_event(
        db,
        church=church,
        creator=author,
        title="Event draft",
    )
    create_event(
        db,
        church=church,
        creator=author,
        title="Published event",
        status=EVENT_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, pastor)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert announcements.json()["count"] == 2

    assert events.status_code == 200
    assert events.json()["count"] == 2


def test_member_cannot_create_church_content(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Member")

    create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )

    db.commit()
    authenticate(app, member)

    announcement = client.post(
        f"/api/v1/churches/{church.id}/announcements",
        json={
            "title": "Forbidden",
            "body": "Member cannot create this.",
        },
    )

    event = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "Forbidden event",
            "starts_at": "2030-01-01T10:00:00",
        },
    )

    assert announcement.status_code == 403
    assert event.status_code == 403


def test_creator_identity_comes_from_authentication(
    client,
    app,
    db,
):
    church = create_church(db)
    leader = create_user(db, "Authenticated Leader")
    other = create_user(db, "Injected User")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    db.commit()
    authenticate(app, leader)

    response = client.post(
        f"/api/v1/churches/{church.id}/announcements",
        json={
            "title": "Trusted identity",
            "body": "Server chooses the author.",
            "author_user_id": other.id,
        },
    )

    assert response.status_code == 201
    assert response.json()["author_user_id"] == leader.id


def test_creator_can_edit_own_draft_but_not_publish(
    client,
    app,
    db,
):
    church = create_church(db)
    leader = create_user(db, "Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    announcement = create_announcement(
        db,
        church=church,
        author=leader,
        title="Original",
    )
    event = create_event(
        db,
        church=church,
        creator=leader,
        title="Original event",
    )

    db.commit()
    authenticate(app, leader)

    edit_announcement = client.patch(
        (
            f"/api/v1/churches/{church.id}/announcements/"
            f"{announcement.id}"
        ),
        json={"title": "Edited"},
    )

    edit_event = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.id}"
        ),
        json={"title": "Edited event"},
    )

    assert edit_announcement.status_code == 200
    assert edit_announcement.json()["title"] == "Edited"

    assert edit_event.status_code == 200
    assert edit_event.json()["title"] == "Edited event"

    publish_announcement = client.patch(
        (
            f"/api/v1/churches/{church.id}/announcements/"
            f"{announcement.id}"
        ),
        json={"status": ANNOUNCEMENT_STATUS_PUBLISHED},
    )

    publish_event = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.id}"
        ),
        json={"status": EVENT_STATUS_PUBLISHED},
    )

    assert publish_announcement.status_code == 403
    assert publish_event.status_code == 403


def test_creator_cannot_edit_another_creators_draft(
    client,
    app,
    db,
):
    church = create_church(db)
    leader = create_user(db, "Leader")
    other = create_user(db, "Other")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    announcement = create_announcement(
        db,
        church=church,
        author=other,
        title="Other draft",
    )
    event = create_event(
        db,
        church=church,
        creator=other,
        title="Other event",
    )

    db.commit()
    authenticate(app, leader)

    announcement_response = client.patch(
        (
            f"/api/v1/churches/{church.id}/announcements/"
            f"{announcement.id}"
        ),
        json={"title": "Hijacked"},
    )

    event_response = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.id}"
        ),
        json={"title": "Hijacked"},
    )

    assert announcement_response.status_code == 403
    assert event_response.status_code == 403


def test_manager_can_publish_archive_and_cancel(
    client,
    app,
    db,
):
    church = create_church(db)
    admin = create_user(db, "Church Admin")
    creator = create_user(db, "Creator")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    announcement = create_announcement(
        db,
        church=church,
        author=creator,
        title="Announcement",
    )
    event = create_event(
        db,
        church=church,
        creator=creator,
        title="Event",
    )

    db.commit()
    authenticate(app, admin)

    published = client.patch(
        (
            f"/api/v1/churches/{church.id}/announcements/"
            f"{announcement.id}"
        ),
        json={"status": ANNOUNCEMENT_STATUS_PUBLISHED},
    )

    assert published.status_code == 200
    assert published.json()["status"] == ANNOUNCEMENT_STATUS_PUBLISHED
    assert published.json()["published_at"] is not None

    archived = client.patch(
        (
            f"/api/v1/churches/{church.id}/announcements/"
            f"{announcement.id}"
        ),
        json={"status": ANNOUNCEMENT_STATUS_ARCHIVED},
    )

    assert archived.status_code == 200
    assert archived.json()["status"] == ANNOUNCEMENT_STATUS_ARCHIVED

    event_published = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.id}"
        ),
        json={"status": EVENT_STATUS_PUBLISHED},
    )

    assert event_published.status_code == 200
    assert event_published.json()["published_at"] is not None

    cancelled = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.id}"
        ),
        json={"status": EVENT_STATUS_CANCELLED},
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == EVENT_STATUS_CANCELLED


def test_invalid_status_is_rejected(
    client,
    app,
    db,
):
    church = create_church(db)
    admin = create_user(db, "Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    db.commit()
    authenticate(app, admin)

    announcement = client.post(
        f"/api/v1/churches/{church.id}/announcements",
        json={
            "title": "Invalid",
            "body": "Invalid status",
            "status": "deleted",
        },
    )

    event = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "Invalid",
            "starts_at": "2030-01-01T10:00:00",
            "status": "deleted",
        },
    )

    assert announcement.status_code == 422
    assert event.status_code == 422


def test_event_end_cannot_precede_start(
    client,
    app,
    db,
):
    church = create_church(db)
    admin = create_user(db, "Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "Impossible event",
            "starts_at": "2030-01-02T10:00:00",
            "ends_at": "2030-01-01T10:00:00",
        },
    )

    assert response.status_code == 422


def test_event_patch_revalidates_combined_dates(
    client,
    app,
    db,
):
    church = create_church(db)
    admin = create_user(db, "Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    event = create_event(
        db,
        church=church,
        creator=admin,
        title="Scheduled event",
    )
    event.ends_at = event.starts_at + timedelta(hours=2)

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.id}"
        ),
        json={
            "starts_at": (
                event.ends_at + timedelta(hours=1)
            ).isoformat()
        },
    )

    assert response.status_code == 422


def test_invalid_event_url_is_rejected(
    client,
    app,
    db,
):
    church = create_church(db)
    admin = create_user(db, "Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "Event",
            "starts_at": "2030-01-01T10:00:00",
            "event_url": "not-a-url",
        },
    )

    assert response.status_code == 422


def test_cross_church_resource_id_is_hidden(
    client,
    app,
    db,
):
    own_church = create_church(db, "Own Church")
    foreign_church = create_church(db, "Foreign Church")

    admin = create_user(db, "Own Admin")
    foreign_creator = create_user(db, "Foreign Creator")

    create_membership(
        db,
        church=own_church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    foreign_announcement = create_announcement(
        db,
        church=foreign_church,
        author=foreign_creator,
        title="Foreign announcement",
    )
    foreign_event = create_event(
        db,
        church=foreign_church,
        creator=foreign_creator,
        title="Foreign event",
    )

    db.commit()
    authenticate(app, admin)

    announcement_response = client.patch(
        (
            f"/api/v1/churches/{own_church.id}/announcements/"
            f"{foreign_announcement.id}"
        ),
        json={"title": "Cross tenant edit"},
    )

    event_response = client.patch(
        (
            f"/api/v1/churches/{own_church.id}/events/"
            f"{foreign_event.id}"
        ),
        json={"title": "Cross tenant edit"},
    )

    assert announcement_response.status_code == 404
    assert event_response.status_code == 404


def test_foreign_church_lists_are_hidden(
    client,
    app,
    db,
):
    own_church = create_church(db, "Own Church")
    foreign_church = create_church(db, "Foreign Church")
    admin = create_user(db, "Admin")

    create_membership(
        db,
        church=own_church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    db.commit()
    authenticate(app, admin)

    announcements = client.get(
        f"/api/v1/churches/{foreign_church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{foreign_church.id}/events"
    )

    assert announcements.status_code == 404
    assert events.status_code == 404


def test_global_admin_has_no_content_bypass(
    client,
    app,
    db,
):
    church = create_church(db, "Protected Church")
    global_admin = create_user(
        db,
        "Global Admin",
        role="admin",
    )

    db.commit()
    authenticate(app, global_admin)

    announcement = client.post(
        f"/api/v1/churches/{church.id}/announcements",
        json={
            "title": "No bypass",
            "body": "Global role is not Church authorization.",
        },
    )

    event = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "No bypass",
            "starts_at": "2030-01-01T10:00:00",
        },
    )

    assert announcement.status_code == 404
    assert event.status_code == 404
def test_group_member_sees_targeted_published_content(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Target Member")
    author = create_user(db, "Target Author")

    church_membership = create_membership(
        db,
        church=church,
        user=member,
    )
    group = create_group(
        db,
        church=church,
        name="Worship Team",
    )
    create_group_membership(
        db,
        group=group,
        church_membership=church_membership,
    )

    announcement = create_announcement(
        db,
        church=church,
        author=author,
        title="Worship announcement",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )
    announcement.target_group_id = group.id

    event = create_event(
        db,
        church=church,
        creator=author,
        title="Worship rehearsal",
        status=EVENT_STATUS_PUBLISHED,
    )
    event.target_group_id = group.id

    db.commit()
    authenticate(app, member)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert [
        item["title"]
        for item in announcements.json()["announcements"]
    ] == ["Worship announcement"]
    assert (
        announcements.json()["announcements"][0]["target_group_id"]
        == group.id
    )

    assert events.status_code == 200
    assert [
        item["title"]
        for item in events.json()["events"]
    ] == ["Worship rehearsal"]
    assert events.json()["events"][0]["target_group_id"] == group.id


def test_non_group_member_cannot_see_targeted_published_content(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Outside Member")
    author = create_user(db, "Outside Author")

    create_membership(
        db,
        church=church,
        user=member,
    )
    group = create_group(
        db,
        church=church,
        name="Leaders Group",
    )

    announcement = create_announcement(
        db,
        church=church,
        author=author,
        title="Leaders only",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )
    announcement.target_group_id = group.id

    event = create_event(
        db,
        church=church,
        creator=author,
        title="Leaders event",
        status=EVENT_STATUS_PUBLISHED,
    )
    event.target_group_id = group.id

    db.commit()
    authenticate(app, member)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert announcements.json()["announcements"] == []

    assert events.status_code == 200
    assert events.json()["events"] == []


@pytest.mark.parametrize(
    "group_member_status",
    [
        GROUP_MEMBER_STATUS_INVITED,
        GROUP_MEMBER_STATUS_LEFT,
    ],
)
def test_non_active_group_membership_does_not_grant_visibility(
    client,
    app,
    db,
    group_member_status,
):
    church = create_church(db)
    member = create_user(
        db,
        f"Lifecycle {group_member_status}",
    )
    author = create_user(
        db,
        f"Lifecycle Author {group_member_status}",
    )

    church_membership = create_membership(
        db,
        church=church,
        user=member,
    )
    group = create_group(
        db,
        church=church,
        name=f"Lifecycle {group_member_status}",
    )
    create_group_membership(
        db,
        group=group,
        church_membership=church_membership,
        status=group_member_status,
    )

    announcement = create_announcement(
        db,
        church=church,
        author=author,
        title="Restricted announcement",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )
    announcement.target_group_id = group.id

    event = create_event(
        db,
        church=church,
        creator=author,
        title="Restricted event",
        status=EVENT_STATUS_PUBLISHED,
    )
    event.target_group_id = group.id

    db.commit()
    authenticate(app, member)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert announcements.json()["count"] == 0

    assert events.status_code == 200
    assert events.json()["count"] == 0


def test_whole_church_content_remains_visible_with_groups_enabled(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Whole Church Member")
    author = create_user(db, "Whole Church Author")

    create_membership(
        db,
        church=church,
        user=member,
    )

    create_announcement(
        db,
        church=church,
        author=author,
        title="Everyone announcement",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )
    create_event(
        db,
        church=church,
        creator=author,
        title="Everyone event",
        status=EVENT_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, member)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert announcements.json()["count"] == 1
    assert (
        announcements.json()["announcements"][0]["target_group_id"]
        is None
    )

    assert events.status_code == 200
    assert events.json()["count"] == 1
    assert events.json()["events"][0]["target_group_id"] is None


def test_foreign_church_group_is_rejected_as_content_target(
    client,
    app,
    db,
):
    church = create_church(db, "Home Church")
    foreign_church = create_church(db, "Foreign Church")
    admin = create_user(db, "Target Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )
    foreign_group = create_group(
        db,
        church=foreign_church,
        name="Foreign Group",
    )

    db.commit()
    authenticate(app, admin)

    announcement = client.post(
        f"/api/v1/churches/{church.id}/announcements",
        json={
            "title": "Wrong tenant",
            "body": "Must fail closed.",
            "target_group_id": foreign_group.id,
        },
    )
    event = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "Wrong tenant event",
            "starts_at": "2030-01-01T10:00:00",
            "target_group_id": foreign_group.id,
        },
    )

    assert announcement.status_code == 422
    assert event.status_code == 422


def test_manager_can_target_and_clear_group_on_content(
    client,
    app,
    db,
):
    church = create_church(db)
    admin = create_user(db, "Target Manager")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )
    group = create_group(
        db,
        church=church,
        name="Young Adults",
    )

    db.commit()
    authenticate(app, admin)

    announcement = client.post(
        f"/api/v1/churches/{church.id}/announcements",
        json={
            "title": "Young Adults",
            "body": "Group announcement.",
            "target_group_id": group.id,
        },
    )
    event = client.post(
        f"/api/v1/churches/{church.id}/events",
        json={
            "title": "Young Adults Event",
            "starts_at": "2030-01-01T10:00:00",
            "target_group_id": group.id,
        },
    )

    assert announcement.status_code == 201
    assert announcement.json()["target_group_id"] == group.id

    assert event.status_code == 201
    assert event.json()["target_group_id"] == group.id

    announcement_clear = client.patch(
        (
            f"/api/v1/churches/{church.id}/announcements/"
            f"{announcement.json()['id']}"
        ),
        json={"target_group_id": None},
    )
    event_clear = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/"
            f"{event.json()['id']}"
        ),
        json={"target_group_id": None},
    )

    assert announcement_clear.status_code == 200
    assert announcement_clear.json()["target_group_id"] is None

    assert event_clear.status_code == 200
    assert event_clear.json()["target_group_id"] is None


def test_manager_sees_targeted_content_without_group_membership(
    client,
    app,
    db,
):
    church = create_church(db)
    pastor = create_user(db, "Target Pastor", role="pastor")
    author = create_user(db, "Target Content Author")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    group = create_group(
        db,
        church=church,
        name="Pastoral Target",
    )

    announcement = create_announcement(
        db,
        church=church,
        author=author,
        title="Targeted manager announcement",
        status=ANNOUNCEMENT_STATUS_PUBLISHED,
    )
    announcement.target_group_id = group.id

    event = create_event(
        db,
        church=church,
        creator=author,
        title="Targeted manager event",
        status=EVENT_STATUS_PUBLISHED,
    )
    event.target_group_id = group.id

    db.commit()
    authenticate(app, pastor)

    announcements = client.get(
        f"/api/v1/churches/{church.id}/announcements"
    )
    events = client.get(
        f"/api/v1/churches/{church.id}/events"
    )

    assert announcements.status_code == 200
    assert announcements.json()["count"] == 1

    assert events.status_code == 200
    assert events.json()["count"] == 1
