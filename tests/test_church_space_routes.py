"""
Route tests for the XynaFaith V2 Church Space API.

These tests use an isolated in-memory database and never connect
to the V1 or V2 PostgreSQL databases.
"""

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
    MEMBERSHIP_STATUS_SUSPENDED,
)
from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.church import Church
from api.models.church_membership import ChurchMembership
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
        denomination="Pentecostal",
        country="Ghana",
        city="Accra",
        is_featured=False,
        is_verified=True,
    )
    db.add(church)
    db.flush()
    return church


def create_user(
    db,
    name,
    *,
    role="member",
):
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
    is_primary=False,
):
    membership = ChurchMembership(
        church_id=church.id,
        user_id=user.id,
        role=role,
        status=status,
        is_primary=is_primary,
    )
    db.add(membership)
    db.flush()
    return membership


def authenticate(app, user):
    app.state.auth["user"] = user


def test_mine_returns_primary_active_church_space(
    client,
    app,
    db,
):
    church = create_church(db)
    user = create_user(db, "Primary Member")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_MEMBER,
        is_primary=True,
    )
    db.commit()

    authenticate(app, user)

    response = client.get("/api/v1/churches/mine")

    assert response.status_code == 200

    data = response.json()

    assert data["church"]["id"] == church.id
    assert data["church"]["name"] == "Grace Church"
    assert data["church"]["city"] == "Accra"
    assert data["church"]["country"] == "Ghana"
    assert data["church"]["is_verified"] is True

    assert data["membership"]["user_id"] == user.id
    assert data["membership"]["role"] == CHURCH_ROLE_MEMBER
    assert data["membership"]["is_primary"] is True

    assert data["permissions"] == [
        "church.view",
        "prayer.view",
    ]

    assert data["capabilities"]["can_manage_church"] is False
    assert data["capabilities"]["can_view_members"] is False
    assert data["capabilities"]["can_view_prayer"] is True


def test_mine_returns_404_without_primary_active_membership(
    client,
    app,
    db,
):
    church = create_church(db)
    user = create_user(db, "No Primary")

    create_membership(
        db,
        church=church,
        user=user,
        is_primary=False,
    )
    db.commit()

    authenticate(app, user)

    response = client.get("/api/v1/churches/mine")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No primary Church Space found",
    }


def test_member_can_open_own_church_space(
    client,
    app,
    db,
):
    church = create_church(db)
    user = create_user(db, "Church Member")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_MEMBER,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/space"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["church"]["id"] == church.id
    assert data["membership"]["role"] == CHURCH_ROLE_MEMBER
    assert "church.view" in data["permissions"]
    assert "members.view" not in data["permissions"]


def test_foreign_church_space_is_hidden(
    client,
    app,
    db,
):
    own_church = create_church(db, "Own Church")
    foreign_church = create_church(db, "Foreign Church")
    user = create_user(db, "Tenant Member")

    create_membership(
        db,
        church=own_church,
        user=user,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{foreign_church.id}/space"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Church Space not found",
    }


def test_inactive_membership_cannot_open_space(
    client,
    app,
    db,
):
    church = create_church(db)
    user = create_user(db, "Suspended Member")

    create_membership(
        db,
        church=church,
        user=user,
        status=MEMBERSHIP_STATUS_SUSPENDED,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/space"
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Church membership is not active",
    }


def test_pastor_can_view_members(
    client,
    app,
    db,
):
    church = create_church(db)

    pastor = create_user(
        db,
        "Pastor User",
        role="pastor",
    )
    member = create_user(db, "Member User")

    create_membership(
        db,
        church=church,
        user=pastor,
        role=CHURCH_ROLE_PASTOR,
        is_primary=True,
    )
    create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )
    db.commit()

    authenticate(app, pastor)

    response = client.get(
        f"/api/v1/churches/{church.id}/members"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["church_id"] == church.id
    assert data["count"] == 2

    users = {
        item["user"]["id"]: item
        for item in data["members"]
    }

    assert users[pastor.id]["role"] == CHURCH_ROLE_PASTOR
    assert users[member.id]["role"] == CHURCH_ROLE_MEMBER


def test_member_cannot_view_member_directory(
    client,
    app,
    db,
):
    church = create_church(db)
    user = create_user(db, "Private Member")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_MEMBER,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{church.id}/members"
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Insufficient Church Space permission",
    }


def test_members_endpoint_hides_foreign_church(
    client,
    app,
    db,
):
    own_church = create_church(db, "Admin Church")
    foreign_church = create_church(db, "Other Church")

    user = create_user(
        db,
        "Church Administrator",
        role="member",
    )

    create_membership(
        db,
        church=own_church,
        user=user,
        role=CHURCH_ROLE_ADMIN,
    )
    db.commit()

    authenticate(app, user)

    response = client.get(
        f"/api/v1/churches/{foreign_church.id}/members"
    )

    assert response.status_code == 404


def test_global_admin_has_no_church_space_bypass(
    client,
    app,
    db,
):
    church = create_church(db, "Protected Church")

    global_admin = create_user(
        db,
        "Global Administrator",
        role="admin",
    )
    db.commit()

    authenticate(app, global_admin)

    space_response = client.get(
        f"/api/v1/churches/{church.id}/space"
    )
    members_response = client.get(
        f"/api/v1/churches/{church.id}/members"
    )

    assert space_response.status_code == 404
    assert members_response.status_code == 404
