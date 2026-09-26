"""
Security and behavior tests for XynaFaith V2 Member Engagement.

These tests use isolated in-memory SQLite and never connect to
the V1 or V2 PostgreSQL databases.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(type_, compiler, **kw):
    # Test-only compatibility shim.
    # Production PostgreSQL continues to use native JSONB.
    return "JSON"


from api.core.dependencies import get_current_user
from api.db.database import Base, get_db
from api.models.member_reading_plan import (
    MemberReadingPlan,
    MemberReadingProgress,
)
from api.models.member_sermon_note import MemberSermonNote
from api.models.reading_plan import ReadingPlan, ReadingPlanDay
from api.models.sermon import Sermon
from api.models.user import User
from api.v1.member.engagement_router import router


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
            User.__table__,
            Sermon.__table__,
            ReadingPlan.__table__,
            ReadingPlanDay.__table__,
            MemberReadingPlan.__table__,
            MemberReadingProgress.__table__,
            MemberSermonNote.__table__,
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
    test_app.include_router(
        router,
        prefix="/api/v1/member",
    )

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


def authenticate(app, user):
    app.state.auth["user"] = user


def create_reading_plan(
    db,
    *,
    title="Seven Days of Faith",
    status="published",
    day_count=2,
):
    plan = ReadingPlan(
        title=title,
        description="A test reading plan",
        duration_days=day_count,
        status=status,
    )
    db.add(plan)
    db.flush()

    days = []

    for day_number in range(1, day_count + 1):
        day = ReadingPlanDay(
            plan_id=plan.id,
            day_number=day_number,
            title=f"Day {day_number}",
            scripture=f"John {day_number}:1",
            reflection=f"Reflection {day_number}",
            prompt=f"Prompt {day_number}",
        )
        db.add(day)
        days.append(day)

    db.flush()
    return plan, days


def create_sermon(db, *, author=None, title="Test Sermon"):
    sermon = Sermon(
        title=title,
        scripture="John 3:16",
        content="Test sermon content",
        author_id=author.id if author else None,
    )
    db.add(sermon)
    db.flush()
    return sermon


def test_reading_plan_catalog_returns_only_published_plans(
    client,
    app,
    db,
):
    user = create_user(db, "Member One")
    authenticate(app, user)

    published, _ = create_reading_plan(
        db,
        title="Published Plan",
        status="published",
    )
    create_reading_plan(
        db,
        title="Draft Plan",
        status="draft",
    )
    db.commit()

    response = client.get("/api/v1/member/reading-plans")

    assert response.status_code == 200

    payload = response.json()
    assert len(payload["reading_plans"]) == 1
    assert payload["reading_plans"][0]["id"] == published.id
    assert payload["reading_plans"][0]["title"] == "Published Plan"


def test_start_reading_plan_creates_enrollment_and_progress(
    client,
    app,
    db,
):
    user = create_user(db, "Reading Member")
    plan, days = create_reading_plan(db, day_count=3)
    db.commit()

    authenticate(app, user)

    response = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "active"
    assert payload["plan"]["id"] == plan.id
    assert payload["total_days"] == 3
    assert payload["completed_days"] == 0
    assert all(day["completed"] is False for day in payload["days"])

    enrollment = (
        db.query(MemberReadingPlan)
        .filter(
            MemberReadingPlan.user_id == user.id,
            MemberReadingPlan.plan_id == plan.id,
        )
        .one()
    )

    progress = (
        db.query(MemberReadingProgress)
        .filter(
            MemberReadingProgress.enrollment_id == enrollment.id
        )
        .all()
    )

    assert len(progress) == len(days)


def test_start_reading_plan_is_idempotent(
    client,
    app,
    db,
):
    user = create_user(db, "Repeat Member")
    plan, _ = create_reading_plan(db)
    db.commit()

    authenticate(app, user)

    first = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )
    second = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    count = (
        db.query(MemberReadingPlan)
        .filter(
            MemberReadingPlan.user_id == user.id,
            MemberReadingPlan.plan_id == plan.id,
        )
        .count()
    )

    assert count == 1


def test_draft_reading_plan_cannot_be_started(
    client,
    app,
    db,
):
    user = create_user(db, "Draft Reader")
    plan, _ = create_reading_plan(
        db,
        status="draft",
    )
    db.commit()

    authenticate(app, user)

    response = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )

    assert response.status_code == 404


def test_reading_progress_completes_entire_plan(
    client,
    app,
    db,
):
    user = create_user(db, "Progress Member")
    plan, days = create_reading_plan(db, day_count=2)
    db.commit()

    authenticate(app, user)

    start = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )
    assert start.status_code == 200

    enrollment_id = start.json()["id"]

    first = client.patch(
        (
            f"/api/v1/member/reading-plans/mine/"
            f"{enrollment_id}/days/{days[0].id}"
        ),
        json={"completed": True},
    )

    assert first.status_code == 200
    assert first.json()["status"] == "active"
    assert first.json()["completed_days"] == 1

    second = client.patch(
        (
            f"/api/v1/member/reading-plans/mine/"
            f"{enrollment_id}/days/{days[1].id}"
        ),
        json={"completed": True},
    )

    assert second.status_code == 200
    assert second.json()["status"] == "completed"
    assert second.json()["completed_days"] == 2
    assert second.json()["completed_at"] is not None


def test_invalid_day_cannot_update_reading_progress(
    client,
    app,
    db,
):
    user = create_user(db, "Invalid Day Member")
    plan, _ = create_reading_plan(db)
    other_plan, other_days = create_reading_plan(
        db,
        title="Other Plan",
    )
    db.commit()

    authenticate(app, user)

    start = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )
    assert start.status_code == 200

    enrollment_id = start.json()["id"]

    response = client.patch(
        (
            f"/api/v1/member/reading-plans/mine/"
            f"{enrollment_id}/days/{other_days[0].id}"
        ),
        json={"completed": True},
    )

    assert other_plan.id != plan.id
    assert response.status_code == 404


def test_member_cannot_access_another_members_enrollment(
    client,
    app,
    db,
):
    owner = create_user(db, "Enrollment Owner")
    outsider = create_user(db, "Enrollment Outsider")
    plan, _ = create_reading_plan(db)
    db.commit()

    authenticate(app, owner)

    start = client.post(
        f"/api/v1/member/reading-plans/{plan.id}/start"
    )
    assert start.status_code == 200

    enrollment_id = start.json()["id"]

    authenticate(app, outsider)

    response = client.get(
        f"/api/v1/member/reading-plans/mine/{enrollment_id}"
    )

    assert response.status_code == 404


def test_sermon_note_crud(
    client,
    app,
    db,
):
    user = create_user(db, "Note Member")
    sermon = create_sermon(db, author=user)
    db.commit()

    authenticate(app, user)

    created = client.post(
        "/api/v1/member/sermon-notes",
        json={
            "sermon_id": sermon.id,
            "title": "Sunday Reflection",
            "body": "Remember this message.",
        },
    )

    assert created.status_code == 200

    note_id = created.json()["id"]
    assert created.json()["sermon_id"] == sermon.id
    assert created.json()["title"] == "Sunday Reflection"

    listed = client.get("/api/v1/member/sermon-notes")

    assert listed.status_code == 200
    assert len(listed.json()["notes"]) == 1
    assert listed.json()["notes"][0]["id"] == note_id

    fetched = client.get(
        f"/api/v1/member/sermon-notes/{note_id}"
    )

    assert fetched.status_code == 200
    assert fetched.json()["body"] == "Remember this message."

    updated = client.patch(
        f"/api/v1/member/sermon-notes/{note_id}",
        json={
            "title": "Updated Reflection",
            "body": "Updated note body.",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Reflection"
    assert updated.json()["body"] == "Updated note body."

    deleted = client.delete(
        f"/api/v1/member/sermon-notes/{note_id}"
    )

    assert deleted.status_code == 200
    assert deleted.json() == {
        "deleted": True,
        "note_id": note_id,
    }

    missing = client.get(
        f"/api/v1/member/sermon-notes/{note_id}"
    )

    assert missing.status_code == 404


def test_sermon_note_can_exist_without_sermon(
    client,
    app,
    db,
):
    user = create_user(db, "Standalone Note Member")
    db.commit()

    authenticate(app, user)

    response = client.post(
        "/api/v1/member/sermon-notes",
        json={
            "title": "Personal Reflection",
            "body": "A standalone spiritual note.",
        },
    )

    assert response.status_code == 200
    assert response.json()["sermon_id"] is None


def test_invalid_sermon_cannot_be_attached_to_note(
    client,
    app,
    db,
):
    user = create_user(db, "Invalid Sermon Member")
    db.commit()

    authenticate(app, user)

    response = client.post(
        "/api/v1/member/sermon-notes",
        json={
            "sermon_id": 999999,
            "title": "Invalid",
            "body": "This should not be created.",
        },
    )

    assert response.status_code == 404


def test_member_cannot_access_or_modify_another_members_note(
    client,
    app,
    db,
):
    owner = create_user(db, "Note Owner")
    outsider = create_user(db, "Note Outsider")
    db.commit()

    authenticate(app, owner)

    created = client.post(
        "/api/v1/member/sermon-notes",
        json={
            "title": "Private Note",
            "body": "Only the owner should see this.",
        },
    )

    assert created.status_code == 200
    note_id = created.json()["id"]

    authenticate(app, outsider)

    fetched = client.get(
        f"/api/v1/member/sermon-notes/{note_id}"
    )
    assert fetched.status_code == 404

    updated = client.patch(
        f"/api/v1/member/sermon-notes/{note_id}",
        json={
            "title": "Hijacked",
            "body": "Should not work.",
        },
    )
    assert updated.status_code == 404

    deleted = client.delete(
        f"/api/v1/member/sermon-notes/{note_id}"
    )
    assert deleted.status_code == 404

    authenticate(app, owner)

    still_there = client.get(
        f"/api/v1/member/sermon-notes/{note_id}"
    )

    assert still_there.status_code == 200
    assert still_there.json()["title"] == "Private Note"


def test_blank_sermon_note_body_is_rejected(
    client,
    app,
    db,
):
    user = create_user(db, "Blank Note Member")
    db.commit()

    authenticate(app, user)

    response = client.post(
        "/api/v1/member/sermon-notes",
        json={
            "title": "Blank",
            "body": "   ",
        },
    )

    assert response.status_code == 422
