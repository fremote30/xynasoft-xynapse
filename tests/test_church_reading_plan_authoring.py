"""
Security and behavior tests for XynaFaith V2 Church Reading Plan authoring.

These tests use isolated in-memory SQLite and never connect to
the V1 or V2 PostgreSQL databases.
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
    CHURCH_ROLE_MINISTRY_LEADER,
    MEMBERSHIP_STATUS_ACTIVE,
)
from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.reading_plan import (
    READING_PLAN_STATUS_ARCHIVED,
    READING_PLAN_STATUS_DRAFT,
    READING_PLAN_STATUS_PUBLISHED,
    ReadingPlan,
    ReadingPlanDay,
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
            ReadingPlan.__table__,
            ReadingPlanDay.__table__,
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
    # Authoring/RBAC tests isolate the entitlement boundary.
    # The entitlement engine itself has dedicated service tests.
    monkeypatch.setattr(
        "api.v1.churches.reading_plan_router.has_entitlement",
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


def create_membership(
    db,
    *,
    church,
    user,
    role,
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


def create_plan(
    db,
    *,
    church,
    creator,
    title,
    status=READING_PLAN_STATUS_DRAFT,
):
    plan = ReadingPlan(
        church_id=church.id,
        creator_user_id=creator.id,
        title=title,
        description=f"{title} description",
        duration_days=0,
        status=status,
    )
    db.add(plan)
    db.flush()
    return plan


def authenticate(app, user):
    app.state.auth["user"] = user


def test_content_creator_can_create_draft(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    leader = create_user(db, "Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    db.commit()
    authenticate(app, leader)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans",
        json={
            "title": "Seven Days of Faith",
            "description": "A church reading journey",
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["church_id"] == church.id
    assert payload["creator_user_id"] == leader.id
    assert payload["title"] == "Seven Days of Faith"
    assert payload["duration_days"] == 0
    assert payload["status"] == READING_PLAN_STATUS_DRAFT
    assert payload["published_at"] is None
    assert payload["days"] == []


def test_member_without_content_create_cannot_create_plan(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    member = create_user(db, "Member")

    create_membership(
        db,
        church=church,
        user=member,
        role=CHURCH_ROLE_MEMBER,
    )

    db.commit()
    authenticate(app, member)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans",
        json={"title": "Forbidden Plan"},
    )

    assert response.status_code == 403


def test_creator_sees_published_and_own_drafts_only(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    leader = create_user(db, "Leader")
    other = create_user(db, "Other Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    own_draft = create_plan(
        db,
        church=church,
        creator=leader,
        title="Own Draft",
    )

    create_plan(
        db,
        church=church,
        creator=other,
        title="Other Draft",
    )

    published = create_plan(
        db,
        church=church,
        creator=other,
        title="Published Plan",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, leader)

    response = client.get(
        f"/api/v1/churches/{church.id}/reading-plans"
    )

    assert response.status_code == 200

    ids = {
        item["id"]
        for item in response.json()["reading_plans"]
    }

    assert ids == {
        own_draft.id,
        published.id,
    }


def test_manager_sees_all_church_plans(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    admin = create_user(db, "Admin")
    creator = create_user(db, "Creator")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    first = create_plan(
        db,
        church=church,
        creator=creator,
        title="Draft",
    )

    second = create_plan(
        db,
        church=church,
        creator=creator,
        title="Published",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, admin)

    response = client.get(
        f"/api/v1/churches/{church.id}/reading-plans"
    )

    assert response.status_code == 200

    ids = {
        item["id"]
        for item in response.json()["reading_plans"]
    }

    assert ids == {first.id, second.id}


def test_plan_lookup_is_scoped_to_church(
    client,
    app,
    db,
):
    church_a = create_church(db, "Church A")
    church_b = create_church(db, "Church B")
    admin = create_user(db, "Admin")
    creator = create_user(db, "Creator")

    create_membership(
        db,
        church=church_a,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    foreign_plan = create_plan(
        db,
        church=church_b,
        creator=creator,
        title="Foreign Plan",
    )

    db.commit()
    authenticate(app, admin)

    response = client.get(
        f"/api/v1/churches/{church_a.id}/reading-plans/"
        f"{foreign_plan.id}"
    )

    assert response.status_code == 404


def test_creator_can_edit_own_draft(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    leader = create_user(db, "Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Original",
    )

    db.commit()
    authenticate(app, leader)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}",
        json={
            "title": "Updated",
            "description": "Updated description",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["description"] == "Updated description"


def test_creator_cannot_edit_another_creators_draft(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    leader = create_user(db, "Leader")
    other = create_user(db, "Other")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=other,
        title="Other Draft",
    )

    db.commit()
    authenticate(app, leader)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}",
        json={"title": "Unauthorized Change"},
    )

    assert response.status_code == 403


def test_creator_cannot_edit_published_plan(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    leader = create_user(db, "Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Published",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, leader)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}",
        json={"title": "Changed"},
    )

    assert response.status_code == 403


def test_manager_can_edit_church_draft(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    admin = create_user(db, "Admin")
    creator = create_user(db, "Creator")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=creator,
        title="Draft",
    )

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}",
        json={"title": "Admin Updated"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Admin Updated"


def test_status_cannot_be_changed_through_generic_patch(
    client,
    app,
    db,
):
    church = create_church(db, "Grace Church")
    admin = create_user(db, "Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Draft",
    )

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}",
        json={"status": READING_PLAN_STATUS_PUBLISHED},
    )

    assert response.status_code == 422

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_DRAFT

def test_missing_reading_plan_entitlement_returns_403(
    client,
    app,
    db,
    monkeypatch,
):
    church = create_church(db, "Grace Church")
    leader = create_user(db, "Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    db.commit()
    authenticate(app, leader)

    monkeypatch.setattr(
        "api.v1.churches.reading_plan_router.has_entitlement",
        lambda db, user, entitlement_key, church_id=None: False,
    )

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans",
        json={"title": "Blocked Plan"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Reading Plans are not available for this account"
    )

    assert db.query(ReadingPlan).count() == 0



def test_creator_can_add_day_and_duration_is_derived(
    client,
    app,
    db,
):
    church = create_church(db, "Day Create Church")
    leader = create_user(db, "Day Creator")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Draft Plan",
    )

    db.commit()
    authenticate(app, leader)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}/days",
        json={
            "day_number": 1,
            "title": "Begin",
            "scripture": "John 1:1",
            "reflection": "Reflect on the beginning.",
            "prompt": "What stands out?",
        },
    )

    assert response.status_code == 201
    assert response.json()["day_number"] == 1
    assert response.json()["scripture"] == "John 1:1"

    db.refresh(plan)
    assert plan.duration_days == 1
    assert (
        db.query(ReadingPlanDay)
        .filter(ReadingPlanDay.plan_id == plan.id)
        .count()
        == 1
    )


def test_duration_counts_actual_days_not_highest_day_number(
    client,
    app,
    db,
):
    church = create_church(db, "Duration Church")
    leader = create_user(db, "Duration Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Draft Plan",
    )

    db.commit()
    authenticate(app, leader)

    for day_number in (1, 3):
        response = client.post(
            f"/api/v1/churches/{church.id}/reading-plans/{plan.id}/days",
            json={
                "day_number": day_number,
                "scripture": f"Psalm {day_number}:1",
            },
        )
        assert response.status_code == 201

    db.refresh(plan)
    assert plan.duration_days == 2


def test_duplicate_day_number_is_rejected(
    client,
    app,
    db,
):
    church = create_church(db, "Duplicate Church")
    leader = create_user(db, "Duplicate Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Draft Plan",
    )

    db.commit()
    authenticate(app, leader)

    first = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}/days",
        json={
            "day_number": 1,
            "scripture": "Genesis 1:1",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/{plan.id}/days",
        json={
            "day_number": 1,
            "scripture": "John 1:1",
        },
    )

    assert duplicate.status_code == 409

    assert (
        db.query(ReadingPlanDay)
        .filter(ReadingPlanDay.plan_id == plan.id)
        .count()
        == 1
    )


def test_creator_can_update_own_draft_day(
    client,
    app,
    db,
):
    church = create_church(db, "Update Day Church")
    leader = create_user(db, "Update Day Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Draft Plan",
    )

    day = ReadingPlanDay(
        plan_id=plan.id,
        day_number=1,
        scripture="John 1:1",
    )
    db.add(day)
    plan.duration_days = 1

    db.commit()
    authenticate(app, leader)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/days/{day.id}",
        json={
            "day_number": 2,
            "title": "Updated Day",
            "scripture": "John 1:2",
        },
    )

    assert response.status_code == 200
    assert response.json()["day_number"] == 2
    assert response.json()["title"] == "Updated Day"
    assert response.json()["scripture"] == "John 1:2"

    db.refresh(plan)
    assert plan.duration_days == 1


def test_day_lookup_cannot_cross_plans(
    client,
    app,
    db,
):
    church = create_church(db, "Plan Isolation Church")
    admin = create_user(db, "Plan Isolation Admin")
    creator = create_user(db, "Plan Isolation Creator")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan_a = create_plan(
        db,
        church=church,
        creator=creator,
        title="Plan A",
    )
    plan_b = create_plan(
        db,
        church=church,
        creator=creator,
        title="Plan B",
    )

    day_b = ReadingPlanDay(
        plan_id=plan_b.id,
        day_number=1,
        scripture="Romans 1:1",
    )
    db.add(day_b)

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan_a.id}/days/{day_b.id}",
        json={"title": "Cross-plan mutation"},
    )

    assert response.status_code == 404

    db.refresh(day_b)
    assert day_b.title is None


def test_day_mutation_cannot_cross_churches(
    client,
    app,
    db,
):
    church_a = create_church(db, "Day Church A")
    church_b = create_church(db, "Day Church B")
    admin = create_user(db, "Day Isolation Admin")
    creator = create_user(db, "Day Isolation Creator")

    create_membership(
        db,
        church=church_a,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    foreign_plan = create_plan(
        db,
        church=church_b,
        creator=creator,
        title="Foreign Plan",
    )

    foreign_day = ReadingPlanDay(
        plan_id=foreign_plan.id,
        day_number=1,
        scripture="Matthew 1:1",
    )
    db.add(foreign_day)

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        f"/api/v1/churches/{church_a.id}/reading-plans/"
        f"{foreign_plan.id}/days/{foreign_day.id}",
        json={"title": "Forbidden"},
    )

    assert response.status_code == 404


def test_creator_cannot_mutate_another_creators_draft_day(
    client,
    app,
    db,
):
    church = create_church(db, "Ownership Church")
    leader = create_user(db, "Ownership Leader")
    other = create_user(db, "Ownership Other")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=other,
        title="Other Draft",
    )

    day = ReadingPlanDay(
        plan_id=plan.id,
        day_number=1,
        scripture="Luke 1:1",
    )
    db.add(day)

    db.commit()
    authenticate(app, leader)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/days/{day.id}",
        json={"title": "Unauthorized"},
    )

    assert response.status_code == 403


def test_manager_can_mutate_another_creators_draft_day(
    client,
    app,
    db,
):
    church = create_church(db, "Manager Day Church")
    admin = create_user(db, "Manager Day Admin")
    creator = create_user(db, "Manager Day Creator")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=creator,
        title="Draft",
    )

    day = ReadingPlanDay(
        plan_id=plan.id,
        day_number=1,
        scripture="Acts 1:1",
    )
    db.add(day)

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/days/{day.id}",
        json={"title": "Managed"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Managed"


def test_even_manager_cannot_mutate_published_plan_days(
    client,
    app,
    db,
):
    church = create_church(db, "Published Day Church")
    admin = create_user(db, "Published Day Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Published",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    day = ReadingPlanDay(
        plan_id=plan.id,
        day_number=1,
        scripture="Hebrews 1:1",
    )
    db.add(day)
    plan.duration_days = 1

    db.commit()
    authenticate(app, admin)

    response = client.patch(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/days/{day.id}",
        json={"title": "Should Not Change"},
    )

    assert response.status_code == 409

    db.refresh(day)
    assert day.title is None


def test_delete_day_recalculates_duration(
    client,
    app,
    db,
):
    church = create_church(db, "Delete Day Church")
    leader = create_user(db, "Delete Day Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Draft",
    )

    day_one = ReadingPlanDay(
        plan_id=plan.id,
        day_number=1,
        scripture="Psalm 1:1",
    )
    day_two = ReadingPlanDay(
        plan_id=plan.id,
        day_number=2,
        scripture="Psalm 2:1",
    )

    db.add_all([day_one, day_two])
    plan.duration_days = 2

    db.commit()
    authenticate(app, leader)

    response = client.delete(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/days/{day_one.id}"
    )

    assert response.status_code == 204

    db.refresh(plan)
    assert plan.duration_days == 1

    remaining = (
        db.query(ReadingPlanDay)
        .filter(ReadingPlanDay.plan_id == plan.id)
        .all()
    )

    assert len(remaining) == 1
    assert remaining[0].id == day_two.id


def test_published_plan_day_cannot_be_deleted(
    client,
    app,
    db,
):
    church = create_church(db, "Published Delete Church")
    admin = create_user(db, "Published Delete Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Published",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    day = ReadingPlanDay(
        plan_id=plan.id,
        day_number=1,
        scripture="James 1:1",
    )
    db.add(day)
    plan.duration_days = 1

    db.commit()
    authenticate(app, admin)

    response = client.delete(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/days/{day.id}"
    )

    assert response.status_code == 409

    assert db.get(ReadingPlanDay, day.id) is not None


def test_manager_can_publish_valid_draft(
    client,
    app,
    db,
):
    church = create_church(db, "Publish Church")
    admin = create_user(db, "Publish Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Publish Me",
    )

    db.add_all(
        [
            ReadingPlanDay(
                plan_id=plan.id,
                day_number=1,
                scripture="John 1:1",
            ),
            ReadingPlanDay(
                plan_id=plan.id,
                day_number=2,
                scripture="John 1:2",
            ),
        ]
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/publish"
    )

    assert response.status_code == 200
    assert response.json()["status"] == READING_PLAN_STATUS_PUBLISHED
    assert response.json()["duration_days"] == 2
    assert response.json()["published_at"] is not None

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_PUBLISHED
    assert plan.duration_days == 2
    assert plan.published_at is not None


def test_content_creator_without_manage_cannot_publish(
    client,
    app,
    db,
):
    church = create_church(db, "Publish RBAC Church")
    leader = create_user(db, "Publish Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Leader Draft",
    )

    db.add(
        ReadingPlanDay(
            plan_id=plan.id,
            day_number=1,
            scripture="Psalm 1:1",
        )
    )

    db.commit()
    authenticate(app, leader)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/publish"
    )

    assert response.status_code == 403

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_DRAFT


def test_empty_plan_cannot_be_published(
    client,
    app,
    db,
):
    church = create_church(db, "Empty Publish Church")
    admin = create_user(db, "Empty Publish Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Empty Draft",
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/publish"
    )

    assert response.status_code == 409

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_DRAFT
    assert plan.published_at is None


def test_plan_with_day_number_gap_cannot_be_published(
    client,
    app,
    db,
):
    church = create_church(db, "Gap Publish Church")
    admin = create_user(db, "Gap Publish Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Gap Draft",
    )

    db.add_all(
        [
            ReadingPlanDay(
                plan_id=plan.id,
                day_number=1,
                scripture="Genesis 1:1",
            ),
            ReadingPlanDay(
                plan_id=plan.id,
                day_number=3,
                scripture="Genesis 1:3",
            ),
        ]
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/publish"
    )

    assert response.status_code == 409

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_DRAFT


def test_published_plan_cannot_be_published_again(
    client,
    app,
    db,
):
    church = create_church(db, "Republish Church")
    admin = create_user(db, "Republish Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Already Published",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    db.add(
        ReadingPlanDay(
            plan_id=plan.id,
            day_number=1,
            scripture="Romans 1:1",
        )
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/publish"
    )

    assert response.status_code == 409


def test_manager_can_archive_published_plan(
    client,
    app,
    db,
):
    church = create_church(db, "Archive Church")
    admin = create_user(db, "Archive Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Archive Me",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    db.add(
        ReadingPlanDay(
            plan_id=plan.id,
            day_number=1,
            scripture="Acts 1:1",
        )
    )
    plan.duration_days = 1

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/archive"
    )

    assert response.status_code == 200
    assert response.json()["status"] == READING_PLAN_STATUS_ARCHIVED

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_ARCHIVED


def test_content_creator_without_manage_cannot_archive(
    client,
    app,
    db,
):
    church = create_church(db, "Archive RBAC Church")
    leader = create_user(db, "Archive Leader")

    create_membership(
        db,
        church=church,
        user=leader,
        role=CHURCH_ROLE_MINISTRY_LEADER,
    )

    plan = create_plan(
        db,
        church=church,
        creator=leader,
        title="Published Plan",
        status=READING_PLAN_STATUS_PUBLISHED,
    )

    db.commit()
    authenticate(app, leader)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/archive"
    )

    assert response.status_code == 403

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_PUBLISHED


def test_draft_plan_cannot_be_archived(
    client,
    app,
    db,
):
    church = create_church(db, "Draft Archive Church")
    admin = create_user(db, "Draft Archive Admin")

    create_membership(
        db,
        church=church,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    plan = create_plan(
        db,
        church=church,
        creator=admin,
        title="Draft",
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church.id}/reading-plans/"
        f"{plan.id}/archive"
    )

    assert response.status_code == 409

    db.refresh(plan)
    assert plan.status == READING_PLAN_STATUS_DRAFT


def test_publish_cannot_cross_church_boundary(
    client,
    app,
    db,
):
    church_a = create_church(db, "Lifecycle Church A")
    church_b = create_church(db, "Lifecycle Church B")

    admin = create_user(db, "Lifecycle Admin")
    creator = create_user(db, "Lifecycle Creator")

    create_membership(
        db,
        church=church_a,
        user=admin,
        role=CHURCH_ROLE_ADMIN,
    )

    foreign_plan = create_plan(
        db,
        church=church_b,
        creator=creator,
        title="Foreign Draft",
    )

    db.add(
        ReadingPlanDay(
            plan_id=foreign_plan.id,
            day_number=1,
            scripture="Mark 1:1",
        )
    )

    db.commit()
    authenticate(app, admin)

    response = client.post(
        f"/api/v1/churches/{church_a.id}/reading-plans/"
        f"{foreign_plan.id}/publish"
    )

    assert response.status_code == 404

    db.refresh(foreign_plan)
    assert foreign_plan.status == READING_PLAN_STATUS_DRAFT
