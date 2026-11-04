"""Security and behavior tests for XynaFaith V2 Church Operations."""

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
from api.models.church_attendance import ChurchAttendanceRecord
from api.models.church_event import ChurchEvent
from api.models.church_group import (
    GROUP_MEMBER_STATUS_ACTIVE,
    GROUP_STATUS_ACTIVE,
    GROUP_TYPE_MINISTRY,
    GROUP_TYPE_TEAM,
    ChurchGroup,
    ChurchGroupMembership,
)
from api.models.church_membership import ChurchMembership
from api.models.church_service_assignment import ChurchServiceAssignment
from api.models.user import User
from api.v1.churches.router import router
import api.services.church_operations_service as operations_service


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
            ChurchEvent.__table__,
            ChurchAttendanceRecord.__table__,
            ChurchServiceAssignment.__table__,
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


def create_user(db, name):
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '-')}@example.test",
        password="not-a-real-password",
        role="member",
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


def create_event(db, *, church, creator):
    event = ChurchEvent(
        church_id=church.id,
        created_by_user_id=creator.id,
        title="Sunday Service",
        starts_at=datetime.utcnow() + timedelta(days=1),
        status="published",
    )
    db.add(event)
    db.flush()
    return event


def create_group(db, *, church, name, group_type):
    group = ChurchGroup(
        church_id=church.id,
        name=name,
        group_type=group_type,
        status=GROUP_STATUS_ACTIVE,
    )
    db.add(group)
    db.flush()
    return group


def add_group_member(db, *, group, membership):
    group_membership = ChurchGroupMembership(
        group_id=group.id,
        church_membership_id=membership.id,
        role="member",
        status=GROUP_MEMBER_STATUS_ACTIVE,
    )
    db.add(group_membership)
    db.flush()
    return group_membership


def authenticate(app, user):
    app.state.auth["user"] = user


def grant_entitlements(monkeypatch):
    monkeypatch.setattr(
        operations_service,
        "has_entitlement",
        lambda *args, **kwargs: True,
    )


def test_pastor_records_attendance(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor One")
    member = create_user(db, "Member One")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )
    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        f"/api/v1/churches/{church.id}/events/{event.id}/attendance",
        json={
            "church_membership_id": member_membership.id,
            "status": "present",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["event_id"] == event.id
    assert payload["church_membership_id"] == member_membership.id
    assert payload["status"] == "present"
    assert payload["checked_in_at"] is not None


def test_ordinary_member_cannot_access_attendance_roster(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    member = create_user(db, "Member Two")
    create_membership(
        db,
        church=church,
        user=member,
    )
    event = create_event(
        db,
        church=church,
        creator=member,
    )
    db.commit()

    authenticate(app, member)

    response = client.get(
        f"/api/v1/churches/{church.id}/events/{event.id}/attendance"
    )

    assert response.status_code == 403


def test_attendance_rejects_foreign_church_member(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    other = create_church(db, "Other Church")
    pastor = create_user(db, "Pastor Two")
    foreign_user = create_user(db, "Foreign Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    foreign_membership = create_membership(
        db,
        church=other,
        user=foreign_user,
    )
    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        f"/api/v1/churches/{church.id}/events/{event.id}/attendance",
        json={
            "church_membership_id": foreign_membership.id,
            "status": "present",
        },
    )

    assert response.status_code == 404


def test_duplicate_attendance_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor Three")
    member = create_user(db, "Member Three")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )
    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    url = (
        f"/api/v1/churches/{church.id}/events/"
        f"{event.id}/attendance"
    )
    body = {
        "church_membership_id": member_membership.id,
        "status": "present",
    }

    assert client.post(url, json=body).status_code == 201
    assert client.post(url, json=body).status_code == 422


def test_attendance_status_can_be_updated(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor Four")
    member = create_user(db, "Member Four")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )
    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    created = client.post(
        f"/api/v1/churches/{church.id}/events/{event.id}/attendance",
        json={
            "church_membership_id": member_membership.id,
            "status": "present",
        },
    )

    attendance_id = created.json()["id"]

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            f"/attendance/{attendance_id}"
        ),
        json={"status": "excused"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "excused"


def test_service_assignment_requires_team_group(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor Five")
    member = create_user(db, "Member Five")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )

    ministry = create_group(
        db,
        church=church,
        name="Youth Ministry",
        group_type=GROUP_TYPE_MINISTRY,
    )

    add_group_member(
        db,
        group=ministry,
        membership=member_membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        ),
        json={
            "group_id": ministry.id,
            "church_membership_id": member_membership.id,
            "service_role": "Usher",
        },
    )

    assert response.status_code == 422


def test_service_assignment_requires_active_team_membership(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor Six")
    member = create_user(db, "Member Six")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )

    team = create_group(
        db,
        church=church,
        name="Media Team",
        group_type=GROUP_TYPE_TEAM,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        ),
        json={
            "group_id": team.id,
            "church_membership_id": member_membership.id,
            "service_role": "Camera",
        },
    )

    assert response.status_code == 422


def test_pastor_assigns_active_team_member(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor Seven")
    member = create_user(db, "Member Seven")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )

    team = create_group(
        db,
        church=church,
        name="Worship Team",
        group_type=GROUP_TYPE_TEAM,
    )
    add_group_member(
        db,
        group=team,
        membership=member_membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        ),
        json={
            "group_id": team.id,
            "church_membership_id": member_membership.id,
            "service_role": "Vocalist",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["group_id"] == team.id
    assert payload["church_membership_id"] == member_membership.id
    assert payload["service_role"] == "Vocalist"
    assert payload["status"] == "assigned"


def test_service_assignment_rejects_foreign_team(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    other = create_church(db, "Other Church")
    pastor = create_user(db, "Pastor Eight")
    member = create_user(db, "Member Eight")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )

    foreign_team = create_group(
        db,
        church=other,
        name="Foreign Team",
        group_type=GROUP_TYPE_TEAM,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.post(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        ),
        json={
            "group_id": foreign_team.id,
            "church_membership_id": member_membership.id,
            "service_role": "Greeter",
        },
    )

    assert response.status_code == 404



def test_service_assignment_rejects_terminal_status_reversal(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Terminal Church")
    pastor = create_user(db, "Terminal Pastor")
    member = create_user(db, "Terminal Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )

    team = create_group(
        db,
        church=church,
        name="Terminal Team",
        group_type=GROUP_TYPE_TEAM,
    )
    add_group_member(
        db,
        group=team,
        membership=member_membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    created = client.post(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        ),
        json={
            "group_id": team.id,
            "church_membership_id": member_membership.id,
            "service_role": "Greeter",
        },
    )
    assert created.status_code == 201
    assignment_id = created.json()["id"]

    for next_status in ("confirmed", "completed"):
        response = client.patch(
            (
                f"/api/v1/churches/{church.id}/events/{event.id}"
                f"/service-assignments/{assignment_id}"
            ),
            json={"status": next_status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == next_status

    reversal = client.patch(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            f"/service-assignments/{assignment_id}"
        ),
        json={"status": "assigned"},
    )

    assert reversal.status_code == 422


def test_service_assignment_status_lifecycle(
    client,
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Grace Church")
    pastor = create_user(db, "Pastor Nine")
    member = create_user(db, "Member Nine")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    member_membership = create_membership(
        db,
        church=church,
        user=member,
    )

    team = create_group(
        db,
        church=church,
        name="Hospitality Team",
        group_type=GROUP_TYPE_TEAM,
    )
    add_group_member(
        db,
        group=team,
        membership=member_membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )
    db.commit()

    authenticate(app, pastor)

    created = client.post(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        ),
        json={
            "group_id": team.id,
            "church_membership_id": member_membership.id,
            "service_role": "Greeter",
        },
    )

    assert created.status_code == 201
    assignment_id = created.json()["id"]

    for next_status in (
        "confirmed",
        "completed",
    ):
        response = client.patch(
            (
                f"/api/v1/churches/{church.id}/events/{event.id}"
                f"/service-assignments/{assignment_id}"
            ),
            json={"status": next_status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == next_status


def test_ordinary_member_cannot_list_service_roster(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    member = create_user(db, "Member Ten")

    create_membership(
        db,
        church=church,
        user=member,
    )

    event = create_event(
        db,
        church=church,
        creator=member,
    )
    db.commit()

    authenticate(app, member)

    response = client.get(
        (
            f"/api/v1/churches/{church.id}/events/{event.id}"
            "/service-assignments"
        )
    )

    assert response.status_code == 403



def test_service_assignment_reassignment_preserves_history(
    app,
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Reassignment Church")
    pastor = create_user(db, "Reassignment Pastor")
    original_member = create_user(db, "Original Member")
    replacement_member = create_user(db, "Replacement Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    original_membership = create_membership(
        db,
        church=church,
        user=original_member,
    )
    replacement_membership = create_membership(
        db,
        church=church,
        user=replacement_member,
    )

    team = create_group(
        db,
        church=church,
        name="Reassignment Team",
        group_type=GROUP_TYPE_TEAM,
    )

    add_group_member(
        db,
        group=team,
        membership=original_membership,
    )
    add_group_member(
        db,
        group=team,
        membership=replacement_membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )

    original = operations_service.create_service_assignment(
        db,
        user=pastor,
        church_id=church.id,
        event_id=event.id,
        group_id=team.id,
        church_membership_id=original_membership.id,
        service_role="Camera",
    )
    original_id = original.id
    db.commit()

    old_assignment, replacement = (
        operations_service.reassign_service_assignment(
            db,
            user=pastor,
            church_id=church.id,
            event_id=event.id,
            assignment_id=original_id,
            group_id=team.id,
            church_membership_id=replacement_membership.id,
            service_role="Camera",
        )
    )

    assert old_assignment.id == original_id
    assert old_assignment.status == "cancelled"

    assert replacement.id != original_id
    assert replacement.event_id == event.id
    assert replacement.group_id == team.id
    assert (
        replacement.church_membership_id
        == replacement_membership.id
    )
    assert replacement.service_role == "Camera"
    assert replacement.status == "assigned"
    assert replacement.assigned_by_user_id == pastor.id

    persisted_original = (
        db.query(ChurchServiceAssignment)
        .filter(
            ChurchServiceAssignment.id == original_id
        )
        .one()
    )

    assert persisted_original.status == "cancelled"


def test_service_assignment_reassignment_rejects_terminal_assignment(
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Terminal Reassignment Church")
    pastor = create_user(db, "Terminal Reassignment Pastor")
    original_member = create_user(
        db,
        "Terminal Original Member",
    )
    replacement_member = create_user(
        db,
        "Terminal Replacement Member",
    )

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    original_membership = create_membership(
        db,
        church=church,
        user=original_member,
    )
    replacement_membership = create_membership(
        db,
        church=church,
        user=replacement_member,
    )

    team = create_group(
        db,
        church=church,
        name="Terminal Reassignment Team",
        group_type=GROUP_TYPE_TEAM,
    )

    add_group_member(
        db,
        group=team,
        membership=original_membership,
    )
    add_group_member(
        db,
        group=team,
        membership=replacement_membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )

    original = operations_service.create_service_assignment(
        db,
        user=pastor,
        church_id=church.id,
        event_id=event.id,
        group_id=team.id,
        church_membership_id=original_membership.id,
        service_role="Usher",
    )

    original.status = "completed"
    db.flush()

    with pytest.raises(
        operations_service.ChurchOperationsValidationError,
        match="cannot be reassigned",
    ):
        operations_service.validate_service_assignment_reassignment_for_user(
            db,
            user=pastor,
            church_id=church.id,
            event_id=event.id,
            assignment_id=original.id,
            group_id=team.id,
            church_membership_id=replacement_membership.id,
            service_role="Usher",
        )


def test_service_assignment_reassignment_rejects_same_target(
    db,
    monkeypatch,
):
    grant_entitlements(monkeypatch)

    church = create_church(db, "Same Target Church")
    pastor = create_user(db, "Same Target Pastor")
    member = create_user(db, "Same Target Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    membership = create_membership(
        db,
        church=church,
        user=member,
    )

    team = create_group(
        db,
        church=church,
        name="Same Target Team",
        group_type=GROUP_TYPE_TEAM,
    )
    add_group_member(
        db,
        group=team,
        membership=membership,
    )

    event = create_event(
        db,
        church=church,
        creator=pastor,
    )

    original = operations_service.create_service_assignment(
        db,
        user=pastor,
        church_id=church.id,
        event_id=event.id,
        group_id=team.id,
        church_membership_id=membership.id,
        service_role="Greeter",
    )

    with pytest.raises(
        operations_service.ChurchOperationsValidationError
    ):
        operations_service.validate_service_assignment_reassignment_for_user(
            db,
            user=pastor,
            church_id=church.id,
            event_id=event.id,
            assignment_id=original.id,
            group_id=team.id,
            church_membership_id=membership.id,
            service_role="Greeter",
        )
