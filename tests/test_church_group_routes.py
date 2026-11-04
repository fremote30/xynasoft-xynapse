"""Security and behavior tests for XynaFaith V2 Church Groups."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.core.church_rbac import (
    CHURCH_ROLE_ADMIN,
    CHURCH_ROLE_MEMBER,
    CHURCH_ROLE_PASTOR,
    MEMBERSHIP_STATUS_ACTIVE,
)
from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.church import Church
from api.models.church_group import (
    GROUP_STATUS_ACTIVE,
    GROUP_STATUS_ARCHIVED,
    ChurchGroup,
    ChurchGroupMembership,
)
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.v1.churches.router import router
import api.services.church_group_service as group_service


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


def create_group(
    db,
    *,
    church,
    name,
    group_type="ministry",
    status=GROUP_STATUS_ACTIVE,
):
    group = ChurchGroup(
        church_id=church.id,
        name=name,
        description=f"{name} description",
        group_type=group_type,
        status=status,
    )
    db.add(group)
    db.flush()
    return group


def authenticate(app, user):
    app.state.auth["user"] = user


def grant_groups(monkeypatch):
    monkeypatch.setattr(
        group_service,
        "has_entitlement",
        lambda *args, **kwargs: True,
    )


def deny_groups(monkeypatch):
    monkeypatch.setattr(
        group_service,
        "has_entitlement",
        lambda *args, **kwargs: False,
    )


def test_member_lists_only_active_groups_in_own_church(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    other = create_church(db, "Other Church")
    user = create_user(db, "Member One")

    create_membership(
        db,
        church=church,
        user=user,
    )

    create_group(db, church=church, name="Youth Ministry")
    create_group(
        db,
        church=church,
        name="Old Team",
        status=GROUP_STATUS_ARCHIVED,
    )
    create_group(db, church=other, name="Foreign Ministry")
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["church_id"] == church.id
    assert [item["name"] for item in payload["groups"]] == [
        "Youth Ministry"
    ]


def test_member_can_view_active_group_detail(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Member Two")
    create_membership(db, church=church, user=user)

    group = create_group(
        db,
        church=church,
        name="Young Adults",
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups/{group.id}"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Young Adults"


def test_member_cannot_discover_archived_group(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Member Three")
    create_membership(db, church=church, user=user)

    group = create_group(
        db,
        church=church,
        name="Archived Group",
        status=GROUP_STATUS_ARCHIVED,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups/{group.id}"
    )

    assert response.status_code == 404


def test_pastor_can_view_archived_group(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Pastor One")
    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_PASTOR,
    )

    group = create_group(
        db,
        church=church,
        name="Archived Group",
        status=GROUP_STATUS_ARCHIVED,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups/{group.id}"
    )

    assert response.status_code == 200
    assert response.json()["status"] == GROUP_STATUS_ARCHIVED


def test_foreign_group_id_fails_closed(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    other = create_church(db, "Other Church")
    user = create_user(db, "Member Four")

    create_membership(db, church=church, user=user)
    foreign_group = create_group(
        db,
        church=other,
        name="Foreign Group",
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups/{foreign_group.id}"
    )

    assert response.status_code == 404


def test_user_cannot_list_foreign_church_groups(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    other = create_church(db, "Other Church")
    user = create_user(db, "Member Five")

    create_membership(db, church=church, user=user)
    create_group(db, church=other, name="Foreign Group")
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{other.id}/groups"
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "role",
    [
        CHURCH_ROLE_ADMIN,
        CHURCH_ROLE_PASTOR,
    ],
)
def test_authorized_manager_can_create_group(
    client,
    app,
    db,
    monkeypatch,
    role,
):
    church = create_church(db, f"{role} Church")
    user = create_user(db, f"{role} User")

    create_membership(
        db,
        church=church,
        user=user,
        role=role,
    )
    db.commit()

    authenticate(app, user)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups",
        json={
            "name": "  Youth Ministry  ",
            "description": "  Students and young adults  ",
            "group_type": "ministry",
        },
    )

    assert response.status_code == 201
    payload = response.json()

    assert payload["church_id"] == church.id
    assert payload["name"] == "Youth Ministry"
    assert payload["description"] == "Students and young adults"
    assert payload["group_type"] == "ministry"
    assert payload["status"] == GROUP_STATUS_ACTIVE


def test_member_cannot_create_group(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Member Six")

    create_membership(db, church=church, user=user)
    db.commit()

    authenticate(app, user)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups",
        json={
            "name": "Unauthorized Group",
            "group_type": "ministry",
        },
    )

    assert response.status_code == 403


def test_manager_requires_groups_entitlement(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Pastor Two")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_PASTOR,
    )
    db.commit()

    authenticate(app, user)
    deny_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups",
        json={
            "name": "Youth Ministry",
            "group_type": "ministry",
        },
    )

    assert response.status_code == 403
    assert "not available" in response.json()["detail"]


def test_invalid_group_type_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Pastor Three")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_PASTOR,
    )
    db.commit()

    authenticate(app, user)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups",
        json={
            "name": "Youth Ministry",
            "group_type": "not-a-real-type",
        },
    )

    assert response.status_code == 422


def test_duplicate_group_name_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Pastor Four")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_PASTOR,
    )
    create_group(
        db,
        church=church,
        name="Youth Ministry",
    )
    db.commit()

    authenticate(app, user)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups",
        json={
            "name": "Youth Ministry",
            "group_type": "ministry",
        },
    )

    assert response.status_code == 422


def test_blank_group_name_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Grace Church")
    user = create_user(db, "Pastor Five")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_PASTOR,
    )
    db.commit()

    authenticate(app, user)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups",
        json={
            "name": "   ",
            "group_type": "ministry",
        },
    )

    assert response.status_code == 422


def test_manager_can_add_same_church_member_to_group(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Membership Church")
    pastor = create_user(db, "Membership Pastor")
    member = create_user(db, "Membership Member")

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
    group = create_group(
        db,
        church=church,
        name="Worship Team",
        group_type="team",
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members",
        json={
            "church_membership_id": member_membership.id,
            "role": "member",
        },
    )

    assert response.status_code == 201
    payload = response.json()

    assert payload["group_id"] == group.id
    assert payload["church_membership_id"] == member_membership.id
    assert payload["role"] == "member"
    assert payload["status"] == "active"


def test_cross_church_membership_assignment_fails_closed(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Home Church")
    foreign_church = create_church(db, "Foreign Church")

    pastor = create_user(db, "Home Pastor")
    foreign_member = create_user(db, "Foreign Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    foreign_membership = create_membership(
        db,
        church=foreign_church,
        user=foreign_member,
    )
    group = create_group(
        db,
        church=church,
        name="Home Ministry",
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members",
        json={
            "church_membership_id": foreign_membership.id,
            "role": "member",
        },
    )

    assert response.status_code == 404

    from api.models.church_group import ChurchGroupMembership

    rows = db.query(ChurchGroupMembership).all()
    assert rows == []


@pytest.mark.parametrize(
    "role",
    [
        "leader",
        "co_leader",
        "member",
    ],
)
def test_supported_group_roles_can_be_assigned(
    client,
    app,
    db,
    monkeypatch,
    role,
):
    church = create_church(db, f"Role {role} Church")
    pastor = create_user(db, f"Role {role} Pastor")
    member = create_user(db, f"Role {role} Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=member,
    )
    group = create_group(
        db,
        church=church,
        name=f"{role} Group",
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members",
        json={
            "church_membership_id": target.id,
            "role": role,
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == role


def test_invalid_group_role_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Invalid Role Church")
    pastor = create_user(db, "Invalid Role Pastor")
    member = create_user(db, "Invalid Role Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=member,
    )
    group = create_group(
        db,
        church=church,
        name="Invalid Role Group",
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members",
        json={
            "church_membership_id": target.id,
            "role": "super-admin",
        },
    )

    assert response.status_code == 422


def test_duplicate_group_membership_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Duplicate Church")
    pastor = create_user(db, "Duplicate Pastor")
    member = create_user(db, "Duplicate Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=member,
    )
    group = create_group(
        db,
        church=church,
        name="Duplicate Group",
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    url = (
        f"/api/v1/churches/{church.id}"
        f"/groups/{group.id}/members"
    )
    payload = {
        "church_membership_id": target.id,
        "role": "member",
    }

    first = client.post(url, json=payload)
    second = client.post(url, json=payload)

    assert first.status_code == 201
    assert second.status_code == 422


def test_member_cannot_administer_group_membership(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Member Security Church")
    actor = create_user(db, "Ordinary Actor")
    target_user = create_user(db, "Target Member")

    create_membership(
        db,
        church=church,
        user=actor,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Protected Group",
    )
    db.commit()

    authenticate(app, actor)
    grant_groups(monkeypatch)

    response = client.post(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members",
        json={
            "church_membership_id": target.id,
            "role": "member",
        },
    )

    assert response.status_code == 403


def create_group_membership(
    db,
    *,
    group,
    church_membership,
    role="member",
    status="active",
):
    membership = ChurchGroupMembership(
        group_id=group.id,
        church_membership_id=church_membership.id,
        role=role,
        status=status,
    )
    db.add(membership)
    db.flush()
    return membership


def test_church_member_can_list_active_group_members(
    client,
    app,
    db,
):
    church = create_church(db, "List Members Church")
    viewer = create_user(db, "List Viewer")
    target_user = create_user(db, "Listed Member")

    create_membership(
        db,
        church=church,
        user=viewer,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Listed Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
        role="leader",
    )
    db.commit()

    authenticate(app, viewer)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members"
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["church_id"] == church.id
    assert payload["group_id"] == group.id
    assert len(payload["members"]) == 1
    assert payload["members"][0]["id"] == group_member.id
    assert payload["members"][0]["role"] == "leader"


def test_left_group_members_are_not_in_active_member_list(
    client,
    app,
    db,
):
    church = create_church(db, "Left Member Church")
    viewer = create_user(db, "Left Viewer")
    active_user = create_user(db, "Still Active")
    left_user = create_user(db, "Already Left")

    create_membership(db, church=church, user=viewer)
    active_membership = create_membership(
        db,
        church=church,
        user=active_user,
    )
    left_membership = create_membership(
        db,
        church=church,
        user=left_user,
    )

    group = create_group(
        db,
        church=church,
        name="Lifecycle Group",
    )

    active_group_member = create_group_membership(
        db,
        group=group,
        church_membership=active_membership,
    )
    create_group_membership(
        db,
        group=group,
        church_membership=left_membership,
        status="left",
    )
    db.commit()

    authenticate(app, viewer)

    response = client.get(
        f"/api/v1/churches/{church.id}/groups/{group.id}/members"
    )

    assert response.status_code == 200

    ids = {
        item["id"]
        for item in response.json()["members"]
    }

    assert active_group_member.id in ids
    assert len(ids) == 1


def test_manager_can_promote_group_member_to_leader(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Promotion Church")
    pastor = create_user(db, "Promotion Pastor")
    target_user = create_user(db, "Future Leader")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Leadership Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{group.id}/members/{group_member.id}"
        ),
        json={"role": "leader"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "leader"

    db.refresh(group_member)
    assert group_member.role == "leader"


def test_manager_can_soft_remove_group_member(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Removal Church")
    pastor = create_user(db, "Removal Pastor")
    target_user = create_user(db, "Removal Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Removal Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.delete(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{group.id}/members/{group_member.id}"
        )
    )

    assert response.status_code == 200
    assert response.json()["status"] == "left"

    db.refresh(group_member)
    assert group_member.status == "left"

    # Historical row remains rather than being destroyed.
    assert (
        db.query(ChurchGroupMembership)
        .filter(ChurchGroupMembership.id == group_member.id)
        .one_or_none()
        is not None
    )


def test_invalid_group_member_status_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Invalid Status Church")
    pastor = create_user(db, "Invalid Status Pastor")
    target_user = create_user(db, "Invalid Status Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Status Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{group.id}/members/{group_member.id}"
        ),
        json={"status": "banned"},
    )

    assert response.status_code == 422


def test_empty_group_member_update_is_rejected(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Empty Update Church")
    pastor = create_user(db, "Empty Update Pastor")
    target_user = create_user(db, "Empty Update Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Empty Update Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{group.id}/members/{group_member.id}"
        ),
        json={},
    )

    assert response.status_code == 422


def test_foreign_group_membership_update_fails_closed(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Update Home Church")
    foreign_church = create_church(db, "Update Foreign Church")

    pastor = create_user(db, "Update Home Pastor")
    foreign_user = create_user(db, "Update Foreign Member")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    foreign_membership = create_membership(
        db,
        church=foreign_church,
        user=foreign_user,
    )

    home_group = create_group(
        db,
        church=church,
        name="Home Update Group",
    )
    foreign_group = create_group(
        db,
        church=foreign_church,
        name="Foreign Update Group",
    )

    foreign_group_member = create_group_membership(
        db,
        group=foreign_group,
        church_membership=foreign_membership,
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{home_group.id}"
            f"/members/{foreign_group_member.id}"
        ),
        json={"role": "leader"},
    )

    assert response.status_code == 404

    db.refresh(foreign_group_member)
    assert foreign_group_member.role == "member"


def test_ordinary_member_cannot_update_group_member(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Mutation Security Church")
    actor = create_user(db, "Mutation Actor")
    target_user = create_user(db, "Mutation Target")

    create_membership(
        db,
        church=church,
        user=actor,
        role=CHURCH_ROLE_MEMBER,
    )
    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Mutation Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
    )
    db.commit()

    authenticate(app, actor)
    grant_groups(monkeypatch)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{group.id}/members/{group_member.id}"
        ),
        json={"role": "leader"},
    )

    assert response.status_code == 403


def test_inactive_church_member_cannot_manage_group_membership(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Inactive Manager Church")
    pastor = create_user(db, "Inactive Manager")
    target_user = create_user(db, "Inactive Manager Target")

    actor_membership = create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
    )
    actor_membership.status = "inactive"

    target = create_membership(
        db,
        church=church,
        user=target_user,
    )
    group = create_group(
        db,
        church=church,
        name="Inactive Manager Group",
    )
    group_member = create_group_membership(
        db,
        group=group,
        church_membership=target,
    )
    db.commit()

    authenticate(app, pastor)
    grant_groups(monkeypatch)

    response = client.patch(
        (
            f"/api/v1/churches/{church.id}"
            f"/groups/{group.id}/members/{group_member.id}"
        ),
        json={"role": "leader"},
    )

    assert response.status_code == 403
