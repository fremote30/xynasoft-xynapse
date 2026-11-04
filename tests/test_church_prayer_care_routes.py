"""
Security and behavior tests for XynaFaith V2 Church Prayer Wall
and Pastoral Care.

These tests use isolated in-memory SQLite and never connect to
the V1 or V2 PostgreSQL databases.
"""

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
    MEMBERSHIP_STATUS_SUSPENDED,
)
from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.pastoral_care_activity import PastoralCareActivity
from api.models.pastoral_care_case import PastoralCareCase
from api.models.pastoral_care_note import PastoralCareNote
from api.models.prayer import Prayer, PrayerRecipient
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
            Prayer.__table__,
            PrayerRecipient.__table__,
            PastoralCareCase.__table__,
            PastoralCareNote.__table__,
            PastoralCareActivity.__table__,
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
    status=MEMBERSHIP_STATUS_ACTIVE,
):
    membership = ChurchMembership(
        church_id=church.id,
        user_id=user.id,
        role=role,
        status=status,
        is_primary=False,
    )
    db.add(membership)
    db.flush()
    return membership


def create_prayer(
    db,
    *,
    church,
    user,
    message="Please pray for me",
    visibility="community",
    pastoral_care_requested=False,
):
    prayer = Prayer(
        user_id=user.id,
        user_name=user.name,
        church_id=church.id,
        message=message,
        visibility=visibility,
        status="still_praying",
        is_anonymous=False,
        pastoral_care_requested=pastoral_care_requested,
    )
    db.add(prayer)
    db.flush()
    return prayer


def authenticate(app, user):
    app.state.auth["user"] = user


def test_member_creates_community_church_prayer(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Prayer Member")
    create_membership(db, church=church, user=member)
    db.commit()

    authenticate(app, member)

    response = client.post(
        f"/api/v1/churches/{church.id}/prayers",
        json={
            "message": "Please pray for my family.",
            "visibility": "community",
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["church_id"] == church.id
    assert data["user_id"] == member.id
    assert data["message"] == "Please pray for my family."
    assert data["visibility"] == "community"
    assert data["pastoral_care_requested"] is False
    assert data["pastoral_care_case"] is None


def test_prayer_and_pastoral_case_are_created_together(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Care Member")
    create_membership(db, church=church, user=member)
    db.commit()

    authenticate(app, member)

    response = client.post(
        f"/api/v1/churches/{church.id}/prayers",
        json={
            "message": "I would like private pastoral follow-up.",
            "visibility": "private",
            "request_pastoral_care": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["pastoral_care_requested"] is True
    assert data["pastoral_care_case"]["status"] == "open"
    assert data["pastoral_care_case"]["priority"] == "routine"

    prayer = db.query(Prayer).one()
    case = db.query(PastoralCareCase).one()
    activity = db.query(PastoralCareActivity).one()

    assert case.prayer_id == prayer.id
    assert case.church_id == church.id
    assert case.member_user_id == member.id
    assert activity.case_id == case.id
    assert activity.church_id == church.id
    assert activity.activity_type == "case_created"


def test_private_prayer_visible_to_owner_but_not_other_member(
    client,
    app,
    db,
):
    church = create_church(db)
    owner = create_user(db, "Prayer Owner")
    other = create_user(db, "Other Member")

    create_membership(db, church=church, user=owner)
    create_membership(db, church=church, user=other)

    prayer = create_prayer(
        db,
        church=church,
        user=owner,
        visibility="private",
    )
    db.commit()

    authenticate(app, owner)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )
    assert response.status_code == 200

    authenticate(app, other)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Prayer not found"


def test_selected_recipient_can_view_private_prayer(
    client,
    app,
    db,
):
    church = create_church(db)
    owner = create_user(db, "Selected Owner")
    recipient = create_user(db, "Selected Recipient")

    create_membership(db, church=church, user=owner)
    create_membership(db, church=church, user=recipient)

    prayer = create_prayer(
        db,
        church=church,
        user=owner,
        visibility="private",
    )

    db.add(
        PrayerRecipient(
            prayer_id=prayer.id,
            recipient_user_id=recipient.id,
            recipient_role="member",
        )
    )
    db.commit()

    authenticate(app, recipient)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == prayer.id


def test_private_care_prayer_stays_off_ordinary_prayer_wall(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Private Member")
    pastor = create_user(db, "Care Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    ordinary_private = create_prayer(
        db,
        church=church,
        user=member,
        message="Ordinary private prayer",
        visibility="private",
        pastoral_care_requested=False,
    )

    care_private = create_prayer(
        db,
        church=church,
        user=member,
        message="Pastoral care prayer",
        visibility="private",
        pastoral_care_requested=True,
    )

    care_case = PastoralCareCase(
        church_id=church.id,
        prayer_id=care_private.id,
        member_user_id=member.id,
        status="open",
        priority="routine",
    )
    db.add(care_case)
    db.commit()

    authenticate(app, pastor)

    ordinary_response = client.get(
        f"/api/v1/churches/{church.id}/prayers/"
        f"{ordinary_private.id}"
    )
    care_wall_response = client.get(
        f"/api/v1/churches/{church.id}/prayers/"
        f"{care_private.id}"
    )
    care_case_response = client.get(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{care_case.id}"
    )

    assert ordinary_response.status_code == 404
    assert care_wall_response.status_code == 404

    assert care_case_response.status_code == 200
    assert (
        care_case_response.json()["prayer"]["id"]
        == care_private.id
    )


def test_foreign_church_prayer_is_tenant_safe_404(
    client,
    app,
    db,
):
    own_church = create_church(db, "Own Church")
    foreign_church = create_church(db, "Foreign Church")

    user = create_user(db, "Tenant Member")
    foreign_owner = create_user(db, "Foreign Owner")

    create_membership(db, church=own_church, user=user)

    prayer = create_prayer(
        db,
        church=foreign_church,
        user=foreign_owner,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{foreign_church.id}/prayers/"
        f"{prayer.id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Church Space not found"


def test_inactive_membership_cannot_access_church_prayers(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Suspended Prayer Member")

    create_membership(
        db,
        church=church,
        user=member,
        status=MEMBERSHIP_STATUS_SUSPENDED,
    )
    db.commit()

    authenticate(app, member)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Church membership is not active"
    )


def test_member_cannot_access_pastoral_care_cases(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Ordinary Member")

    create_membership(db, church=church, user=member)
    db.commit()

    authenticate(app, member)

    response = client.get(
        f"/api/v1/churches/{church.id}/pastoral-care"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Insufficient Church Space permission"
    )


def test_pastor_can_open_care_case_with_private_notes(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Care Recipient")
    pastor = create_user(db, "Pastoral Manager", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        visibility="private",
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=church.id,
        prayer_id=prayer.id,
        member_user_id=member.id,
        status="open",
        priority="routine",
    )
    db.add(case)
    db.flush()

    note = PastoralCareNote(
        case_id=case.id,
        church_id=church.id,
        author_user_id=pastor.id,
        body="Private pastoral note.",
    )
    db.add(note)
    db.commit()

    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["case"]["id"] == case.id
    assert data["prayer"]["id"] == prayer.id
    assert data["notes"][0]["body"] == "Private pastoral note."


def test_private_notes_never_appear_in_prayer_response(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Notes Owner")
    pastor = create_user(db, "Notes Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        visibility="private",
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=church.id,
        prayer_id=prayer.id,
        member_user_id=member.id,
    )
    db.add(case)
    db.flush()

    db.add(
        PastoralCareNote(
            case_id=case.id,
            church_id=church.id,
            author_user_id=pastor.id,
            body="Never expose this note to the member.",
        )
    )
    db.commit()

    authenticate(app, member)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )

    assert response.status_code == 200
    body = response.json()

    assert "notes" not in body
    assert "activities" not in body
    assert "Never expose this note" not in response.text


def test_pastor_can_add_private_note_and_activity_has_no_note_body(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Followup Member")
    pastor = create_user(db, "Followup Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        visibility="private",
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=church.id,
        prayer_id=prayer.id,
        member_user_id=member.id,
    )
    db.add(case)
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}/notes",
        json={"body": "Confidential follow-up details."},
    )

    assert response.status_code == 201
    assert response.json()["body"] == (
        "Confidential follow-up details."
    )

    activity = (
        db.query(PastoralCareActivity)
        .filter(
            PastoralCareActivity.case_id == case.id,
            PastoralCareActivity.activity_type == "note_added",
        )
        .one()
    )

    assert not hasattr(activity, "body")


def test_assignment_requires_same_church_authorized_assignee(
    client,
    app,
    db,
):
    church = create_church(db, "Care Church")
    other_church = create_church(db, "Other Church")

    member = create_user(db, "Assignment Member")
    pastor = create_user(db, "Assigning Pastor", role="pastor")
    ordinary = create_user(db, "Ordinary Assignee")
    foreign_pastor = create_user(db, "Foreign Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    create_membership(db, church=church, user=ordinary)
    create_membership(
        db,
        church=other_church,
        user=foreign_pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=church.id,
        prayer_id=prayer.id,
        member_user_id=member.id,
    )
    db.add(case)
    db.commit()

    authenticate(app, pastor)

    ordinary_response = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={"assigned_to_user_id": ordinary.id},
    )

    assert ordinary_response.status_code == 422
    assert "pastoral_care.manage" in (
        ordinary_response.json()["detail"]
    )

    foreign_response = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={"assigned_to_user_id": foreign_pastor.id},
    )

    assert foreign_response.status_code == 422
    assert "active member" in foreign_response.json()["detail"]

    valid_response = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={"assigned_to_user_id": pastor.id},
    )

    assert valid_response.status_code == 200
    assert valid_response.json()["assigned_to_user_id"] == pastor.id

    activity = (
        db.query(PastoralCareActivity)
        .filter(
            PastoralCareActivity.case_id == case.id,
            PastoralCareActivity.activity_type == "assigned",
        )
        .one()
    )

    assert activity.actor_user_id == pastor.id


def test_case_update_records_follow_up_and_resolution(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Resolution Member")
    pastor = create_user(db, "Resolution Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=church.id,
        prayer_id=prayer.id,
        member_user_id=member.id,
    )
    db.add(case)
    db.commit()

    authenticate(app, pastor)

    follow_up = datetime.utcnow() + timedelta(days=2)

    response = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={
            "status": "resolved",
            "priority": "important",
            "follow_up_at": follow_up.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "resolved"
    assert data["priority"] == "important"
    assert data["follow_up_at"] is not None
    assert data["closed_at"] is None

    activities = {
        item.activity_type
        for item in (
            db.query(PastoralCareActivity)
            .filter(PastoralCareActivity.case_id == case.id)
            .all()
        )
    }

    assert "resolved" in activities
    assert "follow_up_scheduled" in activities


def test_foreign_care_case_is_tenant_safe_404(
    client,
    app,
    db,
):
    own_church = create_church(db, "Pastor Church")
    foreign_church = create_church(db, "Foreign Care Church")

    pastor = create_user(db, "Tenant Pastor", role="pastor")
    foreign_member = create_user(db, "Foreign Care Member")

    create_membership(
        db,
        church=own_church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=foreign_church,
        user=foreign_member,
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=foreign_church.id,
        prayer_id=prayer.id,
        member_user_id=foreign_member.id,
    )
    db.add(case)
    db.commit()

    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{foreign_church.id}/pastoral-care/"
        f"{case.id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Church Space not found"


def test_testimony_text_is_not_shared_without_explicit_consent(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Testimony Member")

    create_membership(db, church=church, user=member)

    prayer = create_prayer(
        db,
        church=church,
        user=member,
    )
    db.commit()

    authenticate(app, member)

    response = client.patch(
        f"/api/v1/churches/{church.id}/prayers/"
        f"{prayer.id}/status",
        json={
            "status": "answered",
            "answer_testimony": "God answered my prayer.",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "answered"
    assert data["answer_testimony"] == "God answered my prayer."
    assert data["testimony_shared_at"] is None


def test_testimony_requires_explicit_share_consent(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Sharing Member")

    create_membership(db, church=church, user=member)

    prayer = create_prayer(
        db,
        church=church,
        user=member,
    )
    db.commit()

    authenticate(app, member)

    response = client.patch(
        f"/api/v1/churches/{church.id}/prayers/"
        f"{prayer.id}/status",
        json={
            "status": "answered",
            "answer_testimony": "A testimony I choose to share.",
            "share_testimony": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["testimony_status"] == "pending"
    assert data["testimony_shared_at"] is None


def test_non_owner_cannot_change_prayer_status(
    client,
    app,
    db,
):
    church = create_church(db)
    owner = create_user(db, "Status Owner")
    pastor = create_user(db, "Status Pastor", role="pastor")

    create_membership(db, church=church, user=owner)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=owner,
        pastoral_care_requested=True,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.patch(
        f"/api/v1/churches/{church.id}/prayers/"
        f"{prayer.id}/status",
        json={"status": "answered"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Prayer not found"


def test_global_admin_role_does_not_bypass_church_membership(
    client,
    app,
    db,
):
    church = create_church(db)
    global_admin = create_user(
        db,
        "Global Admin",
        role="admin",
    )
    db.commit()

    authenticate(app, global_admin)

    prayer_response = client.get(
        f"/api/v1/churches/{church.id}/prayers"
    )
    care_response = client.get(
        f"/api/v1/churches/{church.id}/pastoral-care"
    )

    assert prayer_response.status_code == 404
    assert care_response.status_code == 404

    assert prayer_response.json()["detail"] == (
        "Church Space not found"
    )
    assert care_response.json()["detail"] == (
        "Church Space not found"
    )


def test_pastoral_care_assignees_include_only_authorized_active_members(
    client,
    app,
    db,
):
    church = create_church(db)

    pastor = create_user(db, "Eligible Pastor", role="pastor")
    member = create_user(db, "Ordinary Member")
    suspended_pastor = create_user(
        db,
        "Suspended Pastor",
        role="pastor",
    )

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )
    create_membership(
        db,
        church=church,
        user=suspended_pastor,
        role=CHURCH_ROLE_PASTOR,
        status=MEMBERSHIP_STATUS_SUSPENDED,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{church.id}/"
        "pastoral-care-assignees"
    )

    assert response.status_code == 200

    assignees = response.json()["assignees"]

    assert assignees == [
        {
            "user_id": pastor.id,
            "name": "Eligible Pastor",
            "role": CHURCH_ROLE_PASTOR,
        }
    ]


def test_member_cannot_list_pastoral_care_assignees(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Assignee Viewer")

    create_membership(db, church=church, user=member)
    db.commit()

    authenticate(app, member)

    response = client.get(
        f"/api/v1/churches/{church.id}/"
        "pastoral-care-assignees"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Insufficient Church Space permission"
    )


def test_anonymous_prayer_hides_author_identity_from_other_member(
    client,
    app,
    db,
):
    church = create_church(db)
    author = create_user(db, "Hidden Author")
    viewer = create_user(db, "Prayer Viewer")

    create_membership(db, church=church, user=author)
    create_membership(db, church=church, user=viewer)

    prayer = create_prayer(
        db,
        church=church,
        user=author,
        message="Anonymous community prayer",
        visibility="community",
    )
    prayer.is_anonymous = True
    db.commit()

    authenticate(app, viewer)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] is None
    assert data["user_name"] == "Anonymous"
    assert data["message"] == "Anonymous community prayer"


def test_anonymous_prayer_owner_can_see_own_identity(
    client,
    app,
    db,
):
    church = create_church(db)
    author = create_user(db, "Anonymous Owner")

    create_membership(db, church=church, user=author)

    prayer = create_prayer(
        db,
        church=church,
        user=author,
        message="My anonymous prayer",
        visibility="community",
    )
    prayer.is_anonymous = True
    db.commit()

    authenticate(app, author)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == author.id


def test_mixed_prayer_remains_community_visible(
    client,
    app,
    db,
):
    church = create_church(db)
    author = create_user(db, "Mixed Author")
    viewer = create_user(db, "Mixed Viewer")

    create_membership(db, church=church, user=author)
    create_membership(db, church=church, user=viewer)

    prayer = create_prayer(
        db,
        church=church,
        user=author,
        message="Mixed community prayer",
        visibility="mixed",
    )
    db.commit()

    authenticate(app, viewer)

    response = client.get(
        f"/api/v1/churches/{church.id}/prayers/{prayer.id}"
    )

    assert response.status_code == 200


def test_resolved_case_is_not_closed_until_explicitly_closed(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Care Member")
    pastor = create_user(db, "Lifecycle Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        message="Care lifecycle",
        visibility="private",
        pastoral_care_requested=True,
    )

    case = PastoralCareCase(
        church_id=church.id,
        prayer_id=prayer.id,
        member_user_id=member.id,
        status="open",
        priority="routine",
    )
    db.add(case)
    db.commit()

    authenticate(app, pastor)

    resolved = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={"status": "resolved"},
    )

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["closed_at"] is None

    closed = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={"status": "closed"},
    )

    assert closed.status_code == 200
    assert closed.json()["closed_at"] is not None

    reopened = client.patch(
        f"/api/v1/churches/{church.id}/pastoral-care/"
        f"{case.id}",
        json={"status": "in_progress"},
    )

    assert reopened.status_code == 200
    assert reopened.json()["closed_at"] is None


def test_testimony_consent_creates_pending_not_public_testimony(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Testimony Member")

    create_membership(db, church=church, user=member)

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        message="Please pray",
        visibility="community",
    )
    db.commit()

    authenticate(app, member)

    update = client.patch(
        f"/api/v1/churches/{church.id}/prayers/"
        f"{prayer.id}/status",
        json={
            "status": "answered",
            "answer_testimony": "God answered.",
            "share_testimony": True,
        },
    )

    assert update.status_code == 200
    assert update.json()["testimony_status"] == "pending"
    assert update.json()["testimony_shared_at"] is None

    wall = client.get(
        f"/api/v1/churches/{church.id}/testimonies"
    )

    assert wall.status_code == 200
    assert wall.json()["testimonies"] == []


def test_content_manager_can_approve_pending_testimony(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Answered Member")
    pastor = create_user(db, "Testimony Pastor", role="pastor")

    create_membership(db, church=church, user=member)
    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        message="Private source prayer",
        visibility="private",
    )
    prayer.status = "answered"
    prayer.answer_testimony = "A public testimony."
    prayer.testimony_status = "pending"
    db.commit()

    authenticate(app, pastor)

    pending = client.get(
        f"/api/v1/churches/{church.id}/testimonies/pending"
    )

    assert pending.status_code == 200
    assert pending.json()["count"] == 1

    approval = client.patch(
        f"/api/v1/churches/{church.id}/testimonies/"
        f"{prayer.id}",
        json={"status": "approved"},
    )

    assert approval.status_code == 200
    assert approval.json()["testimony_status"] == "approved"
    assert approval.json()["testimony_shared_at"] is not None

    wall = client.get(
        f"/api/v1/churches/{church.id}/testimonies"
    )

    assert wall.status_code == 200

    testimony = wall.json()["testimonies"][0]

    assert testimony["testimony"] == "A public testimony."
    assert "message" not in testimony
    assert "user_id" not in testimony


def test_member_cannot_moderate_testimony(
    client,
    app,
    db,
):
    church = create_church(db)
    member = create_user(db, "Regular Member")

    create_membership(db, church=church, user=member)

    prayer = create_prayer(
        db,
        church=church,
        user=member,
        message="Prayer",
        visibility="community",
    )
    prayer.status = "answered"
    prayer.answer_testimony = "Pending testimony"
    prayer.testimony_status = "pending"
    db.commit()

    authenticate(app, member)

    response = client.patch(
        f"/api/v1/churches/{church.id}/testimonies/"
        f"{prayer.id}",
        json={"status": "approved"},
    )

    assert response.status_code == 403


def test_testimony_moderation_is_tenant_scoped(
    client,
    app,
    db,
):
    own_church = create_church(db, "Own Testimony Church")
    foreign_church = create_church(
        db,
        "Foreign Testimony Church",
    )

    pastor = create_user(db, "Own Pastor", role="pastor")
    foreign_member = create_user(db, "Foreign Member")

    create_membership(
        db,
        church=own_church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )

    prayer = create_prayer(
        db,
        church=foreign_church,
        user=foreign_member,
        message="Foreign prayer",
        visibility="community",
    )
    prayer.status = "answered"
    prayer.answer_testimony = "Foreign testimony"
    prayer.testimony_status = "pending"
    db.commit()

    authenticate(app, pastor)

    response = client.patch(
        f"/api/v1/churches/{own_church.id}/testimonies/"
        f"{prayer.id}",
        json={"status": "approved"},
    )

    assert response.status_code == 404
