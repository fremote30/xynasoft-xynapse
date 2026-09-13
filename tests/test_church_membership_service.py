"""
XynaFaith V2 Church Space membership authorization tests.

These tests use an isolated in-memory database. They do not connect
to V1 or the V2 development PostgreSQL database.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.church import Church
from api.models.user import User
from api.models.church_membership import ChurchMembership

from api.core.church_rbac import (
    CHURCH_ROLE_ADMIN,
    CHURCH_ROLE_MEMBER,
    CHURCH_ROLE_PASTOR,
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_SUSPENDED,
    MEMBERSHIP_STATUS_LEFT,
    PERMISSION_CHURCH_VIEW,
    PERMISSION_CHURCH_MANAGE,
    PERMISSION_MEMBERS_MANAGE,
    PERMISSION_PASTORAL_CARE_MANAGE,
)

from api.services.church_membership_service import (
    ChurchMembershipNotFound,
    ChurchMembershipInactive,
    ChurchPermissionDenied,
    get_active_church_membership,
    get_primary_church_membership,
    require_church_permission,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Only create the tables required by this service test.
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


def create_church(db, name):
    church = Church(name=name)
    db.add(church)
    db.flush()
    return church


def create_user(db, name, role="member"):
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


def test_active_member_can_view_own_church(db):
    church = create_church(db, "Church A")
    user = create_user(db, "Member A")

    create_membership(
        db,
        church=church,
        user=user,
        is_primary=True,
    )

    membership = require_church_permission(
        db,
        church_id=church.id,
        user_id=user.id,
        permission=PERMISSION_CHURCH_VIEW,
    )

    assert membership.church_id == church.id
    assert membership.user_id == user.id
    assert membership.role == CHURCH_ROLE_MEMBER


def test_cross_tenant_access_is_denied(db):
    church_a = create_church(db, "Church A")
    church_b = create_church(db, "Church B")
    user = create_user(db, "Member A")

    create_membership(
        db,
        church=church_a,
        user=user,
    )

    with pytest.raises(ChurchMembershipNotFound):
        require_church_permission(
            db,
            church_id=church_b.id,
            user_id=user.id,
            permission=PERMISSION_CHURCH_VIEW,
        )


@pytest.mark.parametrize(
    "status",
    [
        MEMBERSHIP_STATUS_INVITED,
        MEMBERSHIP_STATUS_SUSPENDED,
        MEMBERSHIP_STATUS_LEFT,
    ],
)
def test_inactive_memberships_are_denied(db, status):
    church = create_church(
        db,
        f"Church {status}",
    )
    user = create_user(
        db,
        f"User {status}",
    )

    create_membership(
        db,
        church=church,
        user=user,
        status=status,
    )

    with pytest.raises(ChurchMembershipInactive):
        get_active_church_membership(
            db,
            church_id=church.id,
            user_id=user.id,
        )


def test_member_cannot_manage_church(db):
    church = create_church(db, "Member Church")
    user = create_user(db, "Member User")

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_MEMBER,
    )

    with pytest.raises(ChurchPermissionDenied):
        require_church_permission(
            db,
            church_id=church.id,
            user_id=user.id,
            permission=PERMISSION_CHURCH_MANAGE,
        )


def test_pastor_can_manage_pastoral_care(db):
    church = create_church(db, "Pastor Church")
    user = create_user(
        db,
        "Pastor User",
        role="pastor",
    )

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_PASTOR,
    )

    membership = require_church_permission(
        db,
        church_id=church.id,
        user_id=user.id,
        permission=PERMISSION_PASTORAL_CARE_MANAGE,
    )

    assert membership.role == CHURCH_ROLE_PASTOR


def test_church_admin_can_manage_members(db):
    church = create_church(db, "Admin Church")

    # Deliberately keep the legacy global role as member.
    user = create_user(
        db,
        "Church Admin",
        role="member",
    )

    create_membership(
        db,
        church=church,
        user=user,
        role=CHURCH_ROLE_ADMIN,
    )

    membership = require_church_permission(
        db,
        church_id=church.id,
        user_id=user.id,
        permission=PERMISSION_MEMBERS_MANAGE,
    )

    assert membership.role == CHURCH_ROLE_ADMIN


def test_legacy_global_admin_does_not_bypass_membership(db):
    church = create_church(
        db,
        "Protected Church",
    )

    global_admin = create_user(
        db,
        "Global Admin",
        role="admin",
    )

    # No ChurchMembership exists for this user.
    with pytest.raises(ChurchMembershipNotFound):
        require_church_permission(
            db,
            church_id=church.id,
            user_id=global_admin.id,
            permission=PERMISSION_CHURCH_MANAGE,
        )


def test_primary_active_membership_is_resolved(db):
    church = create_church(
        db,
        "Primary Church",
    )
    user = create_user(
        db,
        "Primary User",
    )

    create_membership(
        db,
        church=church,
        user=user,
        is_primary=True,
    )

    membership = get_primary_church_membership(
        db,
        user_id=user.id,
    )

    assert membership is not None
    assert membership.church_id == church.id
    assert membership.status == MEMBERSHIP_STATUS_ACTIVE


def test_no_primary_membership_returns_none(db):
    church = create_church(
        db,
        "Non Primary Church",
    )
    user = create_user(
        db,
        "Non Primary User",
    )

    create_membership(
        db,
        church=church,
        user=user,
        is_primary=False,
    )

    assert (
        get_primary_church_membership(
            db,
            user_id=user.id,
        )
        is None
    )
