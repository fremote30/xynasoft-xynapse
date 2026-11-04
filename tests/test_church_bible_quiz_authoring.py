"""
Isolated XynaFaith V2 Bible Quiz authoring security tests.

No PostgreSQL access or production database changes.
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
from api.models.bible_quiz import (
    BibleQuiz,
    BibleQuizQuestion,
    BibleQuizAttempt,
    BibleQuizAnswer,
)
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.v1.churches.bible_quiz_router import router


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
            BibleQuiz.__table__,
            BibleQuizQuestion.__table__,
            BibleQuizAttempt.__table__,
            BibleQuizAnswer.__table__,
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
    monkeypatch.setattr(
        "api.v1.churches.bible_quiz_router.has_entitlement",
        lambda db, user, entitlement_key, church_id=None: True,
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/churches")
    state = {"user": None}

    def override_db():
        yield db

    def override_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.state.auth = state
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


def make_user(db, name):
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '-')}@example.test",
        password="test-only",
        role="member",
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def make_church(db, name):
    church = Church(
        name=name,
        location="Accra",
        country="Ghana",
        city="Accra",
    )
    db.add(church)
    db.flush()
    return church


def add_member(db, church, user, role):
    membership = ChurchMembership(
        church_id=church.id,
        user_id=user.id,
        role=role,
        status=MEMBERSHIP_STATUS_ACTIVE,
        is_primary=False,
    )
    db.add(membership)
    db.commit()


def quiz_url(church_id):
    return f"/api/v1/churches/{church_id}/bible-quizzes"


def create_quiz(client, app, church, user):
    app.state.auth["user"] = user
    return client.post(
        quiz_url(church.id),
        json={"title": "Genesis Quiz", "difficulty": "beginner"},
    )


def test_admin_can_create_draft_quiz(db, app, client):
    church = make_church(db, "Church A")
    admin = make_user(db, "Admin A")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    response = create_quiz(client, app, church, admin)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "draft"
    assert response.json()["church_id"] == church.id


def test_regular_member_cannot_create_quiz(db, app, client):
    church = make_church(db, "Church B")
    member = make_user(db, "Member B")
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    response = create_quiz(client, app, church, member)

    assert response.status_code == 403


def test_foreign_church_is_not_exposed(db, app, client):
    church_a = make_church(db, "Church C")
    church_b = make_church(db, "Church D")
    leader = make_user(db, "Leader C")
    add_member(db, church_a, leader, CHURCH_ROLE_MINISTRY_LEADER)

    response = create_quiz(client, app, church_b, leader)

    assert response.status_code == 404


def test_author_can_add_question(db, app, client):
    church = make_church(db, "Church E")
    admin = make_user(db, "Admin E")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    quiz_response = create_quiz(client, app, church, admin)
    assert quiz_response.status_code == 201, quiz_response.text
    quiz_id = quiz_response.json()["id"]

    response = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json={
            "position": 1,
            "question_text": "Who built the ark?",
            "option_a": "Moses",
            "option_b": "Noah",
            "option_c": "David",
            "option_d": "Abraham",
            "correct_option": "B",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["correct_option"] == "B"


def test_duplicate_question_position_rejected(db, app, client):
    church = make_church(db, "Church F")
    admin = make_user(db, "Admin F")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    quiz_response = create_quiz(client, app, church, admin)
    assert quiz_response.status_code == 201, quiz_response.text
    quiz_id = quiz_response.json()["id"]

    url = f"{quiz_url(church.id)}/{quiz_id}/questions"
    payload = {
        "position": 1,
        "question_text": "Who built the ark?",
        "option_a": "Moses",
        "option_b": "Noah",
        "option_c": "David",
        "option_d": "Abraham",
        "correct_option": "B",
    }

    assert client.post(url, json=payload).status_code == 201
    assert client.post(url, json=payload).status_code == 409


def test_entitlement_denial_blocks_quiz_creation(
    db, app, client, monkeypatch
):
    church = make_church(db, "Entitlement Church")
    admin = make_user(db, "Entitlement Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    monkeypatch.setattr(
        "api.v1.churches.bible_quiz_router.has_entitlement",
        lambda db, user, entitlement_key, church_id=None: False,
    )

    response = create_quiz(client, app, church, admin)

    assert response.status_code == 403
    assert db.query(BibleQuiz).count() == 0


def test_cross_church_quiz_question_access_denied(
    db, app, client
):
    church_a = make_church(db, "Quiz Church A")
    church_b = make_church(db, "Quiz Church B")

    admin_a = make_user(db, "Quiz Admin A")
    admin_b = make_user(db, "Quiz Admin B")

    add_member(db, church_a, admin_a, CHURCH_ROLE_ADMIN)
    add_member(db, church_b, admin_b, CHURCH_ROLE_ADMIN)

    quiz_response = create_quiz(client, app, church_a, admin_a)
    assert quiz_response.status_code == 201, quiz_response.text

    quiz_id = quiz_response.json()["id"]
    app.state.auth["user"] = admin_b

    response = client.post(
        f"{quiz_url(church_b.id)}/{quiz_id}/questions",
        json={
            "position": 1,
            "question_text": "Who built the ark?",
            "option_a": "Moses",
            "option_b": "Noah",
            "option_c": "David",
            "option_d": "Abraham",
            "correct_option": "B",
        },
    )

    assert response.status_code == 404
    assert db.query(BibleQuizQuestion).count() == 0


def test_nonowner_ministry_leader_cannot_edit_draft(
    db, app, client
):
    church = make_church(db, "Ownership Church")
    creator = make_user(db, "Creator Leader")
    other = make_user(db, "Other Leader")

    add_member(db, church, creator, CHURCH_ROLE_MINISTRY_LEADER)
    add_member(db, church, other, CHURCH_ROLE_MINISTRY_LEADER)

    quiz_response = create_quiz(client, app, church, creator)
    assert quiz_response.status_code == 201, quiz_response.text

    quiz_id = quiz_response.json()["id"]
    app.state.auth["user"] = other

    response = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json={
            "position": 1,
            "question_text": "Who built the ark?",
            "option_a": "Moses",
            "option_b": "Noah",
            "option_c": "David",
            "option_d": "Abraham",
            "correct_option": "B",
        },
    )

    assert response.status_code == 403
    assert db.query(BibleQuizQuestion).count() == 0



def question_payload(position=1):
    return {
        "position": position,
        "question_text": "Who built the ark?",
        "option_a": "Moses",
        "option_b": "Noah",
        "option_c": "David",
        "option_d": "Abraham",
        "correct_option": "B",
    }


def test_cannot_publish_empty_quiz(db, app, client):
    church = make_church(db, "Empty Quiz Church")
    admin = make_user(db, "Empty Quiz Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    publish = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/publish"
    )

    assert publish.status_code == 409


def test_cannot_publish_nonsequential_questions(db, app, client):
    church = make_church(db, "Sequence Church")
    admin = make_user(db, "Sequence Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    base = f"{quiz_url(church.id)}/{quiz_id}"

    added = client.post(
        f"{base}/questions",
        json=question_payload(position=2),
    )
    assert added.status_code == 201, added.text

    publish = client.post(f"{base}/publish")

    assert publish.status_code == 409


def test_ministry_leader_cannot_publish(db, app, client):
    church = make_church(db, "Leader Publish Church")
    leader = make_user(db, "Publish Leader")
    add_member(db, church, leader, CHURCH_ROLE_MINISTRY_LEADER)

    response = create_quiz(client, app, church, leader)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    base = f"{quiz_url(church.id)}/{quiz_id}"

    assert client.post(
        f"{base}/questions",
        json=question_payload(),
    ).status_code == 201

    publish = client.post(f"{base}/publish")

    assert publish.status_code == 403


def test_admin_can_publish_complete_quiz(db, app, client):
    church = make_church(db, "Publish Church")
    admin = make_user(db, "Publish Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    base = f"{quiz_url(church.id)}/{quiz_id}"

    assert client.post(
        f"{base}/questions",
        json=question_payload(),
    ).status_code == 201

    publish = client.post(f"{base}/publish")

    assert publish.status_code == 200, publish.text
    assert publish.json()["status"] == "published"
    assert db.get(BibleQuiz, quiz_id).published_at is not None


def test_published_quiz_questions_are_immutable(db, app, client):
    church = make_church(db, "Immutable Church")
    admin = make_user(db, "Immutable Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    base = f"{quiz_url(church.id)}/{quiz_id}"

    assert client.post(
        f"{base}/questions",
        json=question_payload(),
    ).status_code == 201

    assert client.post(f"{base}/publish").status_code == 200

    second_question = client.post(
        f"{base}/questions",
        json=question_payload(position=2),
    )

    assert second_question.status_code == 409
    assert db.query(BibleQuizQuestion).filter(
        BibleQuizQuestion.quiz_id == quiz_id
    ).count() == 1


def test_admin_can_archive_published_quiz(db, app, client):
    church = make_church(db, "Archive Church")
    admin = make_user(db, "Archive Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    base = f"{quiz_url(church.id)}/{quiz_id}"

    assert client.post(
        f"{base}/questions",
        json=question_payload(),
    ).status_code == 201

    assert client.post(f"{base}/publish").status_code == 200

    archive = client.post(f"{base}/archive")

    assert archive.status_code == 200, archive.text
    assert archive.json()["status"] == "archived"



def create_published_quiz(db, app, client, church, admin):
    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    base = f"{quiz_url(church.id)}/{quiz_id}"

    added = client.post(
        f"{base}/questions",
        json=question_payload(),
    )
    assert added.status_code == 201, added.text

    published = client.post(f"{base}/publish")
    assert published.status_code == 200, published.text

    return quiz_id


def test_member_can_list_published_quizzes(db, app, client):
    church = make_church(db, "List Church")
    admin = make_user(db, "List Admin")
    member = make_user(db, "List Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    app.state.auth["user"] = member

    response = client.get(quiz_url(church.id))

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == quiz_id


def test_member_quiz_detail_hides_answer_keys(db, app, client):
    church = make_church(db, "Safe Detail Church")
    admin = make_user(db, "Safe Detail Admin")
    member = make_user(db, "Safe Detail Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    app.state.auth["user"] = member

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_id}"
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert len(body["questions"]) == 1

    question = body["questions"][0]

    assert "correct_option" not in question
    assert "explanation" not in question
    assert question["option_b"] == "Noah"


def test_draft_quiz_hidden_from_members(db, app, client):
    church = make_church(db, "Draft Hidden Church")
    admin = make_user(db, "Draft Hidden Admin")
    member = make_user(db, "Draft Hidden Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]
    app.state.auth["user"] = member

    detail = client.get(
        f"{quiz_url(church.id)}/{quiz_id}"
    )
    listing = client.get(quiz_url(church.id))

    assert detail.status_code == 404
    assert listing.status_code == 200
    assert listing.json() == []


def test_archived_quiz_hidden_from_members(db, app, client):
    church = make_church(db, "Archived Hidden Church")
    admin = make_user(db, "Archived Hidden Admin")
    member = make_user(db, "Archived Hidden Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    archived = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/archive"
    )
    assert archived.status_code == 200

    app.state.auth["user"] = member

    detail = client.get(
        f"{quiz_url(church.id)}/{quiz_id}"
    )
    listing = client.get(quiz_url(church.id))

    assert detail.status_code == 404
    assert listing.status_code == 200
    assert listing.json() == []


def test_member_cannot_access_foreign_church_quiz(
    db, app, client
):
    church_a = make_church(db, "Member Church A")
    church_b = make_church(db, "Member Church B")

    admin_a = make_user(db, "Member Admin A")
    member_b = make_user(db, "Foreign Member B")

    add_member(db, church_a, admin_a, CHURCH_ROLE_ADMIN)
    add_member(db, church_b, member_b, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church_a, admin_a
    )

    app.state.auth["user"] = member_b

    response = client.get(
        f"{quiz_url(church_a.id)}/{quiz_id}"
    )

    assert response.status_code == 404


def test_suspended_member_cannot_access_quiz(
    db, app, client
):
    church = make_church(db, "Suspended Church")
    admin = make_user(db, "Suspended Admin")
    member = make_user(db, "Suspended Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    membership = (
        db.query(ChurchMembership)
        .filter_by(church_id=church.id, user_id=member.id)
        .one()
    )
    membership.status = "suspended"
    db.commit()

    app.state.auth["user"] = member

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_id}"
    )

    assert response.status_code in (403, 404)



def submit_answers(client, church_id, quiz_id, answers):
    return client.post(
        f"{quiz_url(church_id)}/{quiz_id}/submit",
        json={"answers": answers},
    )


def test_submission_scores_correct_answer(db, app, client):
    church = make_church(db, "Correct Score Church")
    admin = make_user(db, "Correct Score Admin")
    member = make_user(db, "Correct Score Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    question = db.query(BibleQuizQuestion).filter_by(
        quiz_id=quiz_id
    ).one()

    app.state.auth["user"] = member

    response = submit_answers(
        client,
        church.id,
        quiz_id,
        [{"question_id": question.id, "selected_option": "B"}],
    )

    assert response.status_code == 201, response.text
    assert response.json()["score"] == 100
    assert response.json()["correct_answers"] == 1
    assert response.json()["total_questions"] == 1

    attempt = db.query(BibleQuizAttempt).one()
    answer = db.query(BibleQuizAnswer).one()

    assert attempt.user_id == member.id
    assert attempt.status == "submitted"
    assert answer.is_correct == 1


def test_submission_scores_incorrect_answer(db, app, client):
    church = make_church(db, "Incorrect Score Church")
    admin = make_user(db, "Incorrect Score Admin")
    member = make_user(db, "Incorrect Score Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    question = db.query(BibleQuizQuestion).filter_by(
        quiz_id=quiz_id
    ).one()

    app.state.auth["user"] = member

    response = submit_answers(
        client,
        church.id,
        quiz_id,
        [{"question_id": question.id, "selected_option": "A"}],
    )

    assert response.status_code == 201, response.text
    assert response.json()["score"] == 0
    assert response.json()["correct_answers"] == 0
    assert db.query(BibleQuizAnswer).one().is_correct == 0


def test_submission_rejects_missing_answers(db, app, client):
    church = make_church(db, "Missing Answer Church")
    admin = make_user(db, "Missing Answer Admin")
    member = make_user(db, "Missing Answer Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    app.state.auth["user"] = member

    response = submit_answers(
        client, church.id, quiz_id, []
    )

    assert response.status_code == 422
    assert db.query(BibleQuizAttempt).count() == 0


def test_submission_rejects_duplicate_answers(db, app, client):
    church = make_church(db, "Duplicate Answer Church")
    admin = make_user(db, "Duplicate Answer Admin")
    member = make_user(db, "Duplicate Answer Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    question = db.query(BibleQuizQuestion).filter_by(
        quiz_id=quiz_id
    ).one()

    app.state.auth["user"] = member

    answers = [
        {"question_id": question.id, "selected_option": "B"},
        {"question_id": question.id, "selected_option": "B"},
    ]

    response = submit_answers(
        client, church.id, quiz_id, answers
    )

    assert response.status_code == 422
    assert db.query(BibleQuizAttempt).count() == 0


def test_submission_rejects_foreign_question_id(db, app, client):
    church = make_church(db, "Foreign Question Church")
    admin = make_user(db, "Foreign Question Admin")
    member = make_user(db, "Foreign Question Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    app.state.auth["user"] = member

    response = submit_answers(
        client,
        church.id,
        quiz_id,
        [{"question_id": 999999, "selected_option": "B"}],
    )

    assert response.status_code == 422
    assert db.query(BibleQuizAttempt).count() == 0


def test_submission_rejects_draft_quiz(db, app, client):
    church = make_church(db, "Draft Submit Church")
    admin = make_user(db, "Draft Submit Admin")
    member = make_user(db, "Draft Submit Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    response = create_quiz(client, app, church, admin)
    assert response.status_code == 201

    quiz_id = response.json()["id"]
    app.state.auth["user"] = member

    submitted = submit_answers(
        client,
        church.id,
        quiz_id,
        [{"question_id": 999999, "selected_option": "B"}],
    )

    assert submitted.status_code == 404
    assert db.query(BibleQuizAttempt).count() == 0


def test_repeat_submissions_create_separate_attempts(
    db, app, client
):
    church = make_church(db, "Repeat Attempt Church")
    admin = make_user(db, "Repeat Attempt Admin")
    member = make_user(db, "Repeat Attempt Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    question = db.query(BibleQuizQuestion).filter_by(
        quiz_id=quiz_id
    ).one()

    app.state.auth["user"] = member

    answers = [
        {"question_id": question.id, "selected_option": "B"}
    ]

    first = submit_answers(
        client, church.id, quiz_id, answers
    )
    second = submit_answers(
        client, church.id, quiz_id, answers
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    assert first.json()["attempt_id"] != second.json()["attempt_id"]
    assert db.query(BibleQuizAttempt).count() == 2
    assert db.query(BibleQuizAnswer).count() == 2



def submit_published_quiz_for_user(
    db, app, client, church, quiz_id, user, selected="B"
):
    question = db.query(BibleQuizQuestion).filter_by(
        quiz_id=quiz_id
    ).one()

    app.state.auth["user"] = user

    response = submit_answers(
        client,
        church.id,
        quiz_id,
        [
            {
                "question_id": question.id,
                "selected_option": selected,
            }
        ],
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_member_history_only_contains_own_attempts(
    db, app, client
):
    church = make_church(db, "History Ownership Church")
    admin = make_user(db, "History Ownership Admin")
    member_a = make_user(db, "History Member A")
    member_b = make_user(db, "History Member B")

    for user, role in [
        (admin, CHURCH_ROLE_ADMIN),
        (member_a, CHURCH_ROLE_MEMBER),
        (member_b, CHURCH_ROLE_MEMBER),
    ]:
        add_member(db, church, user, role)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    own = submit_published_quiz_for_user(
        db, app, client, church, quiz_id, member_a
    )
    other = submit_published_quiz_for_user(
        db, app, client, church, quiz_id, member_b
    )

    app.state.auth["user"] = member_a

    response = client.get(
        f"{quiz_url(church.id)}/my-attempts"
    )

    assert response.status_code == 200, response.text
    ids = [item["attempt_id"] for item in response.json()]
    assert ids == [own["attempt_id"]]
    assert other["attempt_id"] not in ids


def test_quiz_history_filters_to_requested_quiz(
    db, app, client
):
    church = make_church(db, "History Filter Church")
    admin = make_user(db, "History Filter Admin")
    member = make_user(db, "History Filter Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_a = create_published_quiz(
        db, app, client, church, admin
    )
    quiz_b = create_published_quiz(
        db, app, client, church, admin
    )

    own_a = submit_published_quiz_for_user(
        db, app, client, church, quiz_a, member
    )
    submit_published_quiz_for_user(
        db, app, client, church, quiz_b, member
    )

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_a}/my-attempts"
    )

    assert response.status_code == 200, response.text
    assert [
        item["attempt_id"] for item in response.json()
    ] == [own_a["attempt_id"]]


def test_archived_quiz_attempt_history_remains_available(
    db, app, client
):
    church = make_church(db, "Archived History Church")
    admin = make_user(db, "Archived History Admin")
    member = make_user(db, "Archived History Member")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    quiz_id = create_published_quiz(
        db, app, client, church, admin
    )

    own = submit_published_quiz_for_user(
        db, app, client, church, quiz_id, member
    )

    app.state.auth["user"] = admin

    archived = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/archive"
    )
    assert archived.status_code == 200, archived.text

    app.state.auth["user"] = member

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_id}/my-attempts"
    )

    assert response.status_code == 200, response.text
    assert response.json()[0]["attempt_id"] == own["attempt_id"]


def test_history_excludes_attempts_from_other_churches(
    db, app, client
):
    church_a = make_church(db, "History Church A")
    church_b = make_church(db, "History Church B")

    admin_a = make_user(db, "History Admin A")
    admin_b = make_user(db, "History Admin B")
    member = make_user(db, "History Shared Member")

    add_member(db, church_a, admin_a, CHURCH_ROLE_ADMIN)
    add_member(db, church_b, admin_b, CHURCH_ROLE_ADMIN)
    add_member(db, church_a, member, CHURCH_ROLE_MEMBER)
    add_member(db, church_b, member, CHURCH_ROLE_MEMBER)

    quiz_a = create_published_quiz(
        db, app, client, church_a, admin_a
    )
    quiz_b = create_published_quiz(
        db, app, client, church_b, admin_b
    )

    own_a = submit_published_quiz_for_user(
        db, app, client, church_a, quiz_a, member
    )
    submit_published_quiz_for_user(
        db, app, client, church_b, quiz_b, member
    )

    response = client.get(
        f"{quiz_url(church_a.id)}/my-attempts"
    )

    assert response.status_code == 200, response.text
    assert [
        item["attempt_id"] for item in response.json()
    ] == [own_a["attempt_id"]]


def test_my_attempts_route_is_not_treated_as_quiz_id(
    db, app, client
):
    church = make_church(db, "History Routing Church")
    member = make_user(db, "History Routing Member")

    add_member(db, church, member, CHURCH_ROLE_MEMBER)
    app.state.auth["user"] = member

    response = client.get(
        f"{quiz_url(church.id)}/my-attempts"
    )

    assert response.status_code == 200, response.text
    assert response.json() == []


# Batch 24.85B: HTTP-level draft security acceptance tests.


def test_2485b_creator_draft_detail(db, app, client):
    church = make_church(db, "2485B Creator Church")
    creator = make_user(db, "2485B Creator")
    add_member(db, church, creator, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, church, creator)
    assert created.status_code == 201, created.text
    quiz_id = created.json()["id"]

    question = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json=question_payload(),
    )
    assert question.status_code == 201, question.text

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_id}/author-draft"
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == quiz_id
    assert response.json()["questions"][0]["correct_option"] == "B"


def test_2485b_other_author_cannot_read_draft(db, app, client):
    church = make_church(db, "2485B Author Isolation")
    creator = make_user(db, "2485B First Author")
    other = make_user(db, "2485B Second Author")

    add_member(db, church, creator, CHURCH_ROLE_ADMIN)
    add_member(db, church, other, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, church, creator)
    assert created.status_code == 201
    quiz_id = created.json()["id"]

    app.state.auth["user"] = other

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_id}/author-draft"
    )

    assert response.status_code == 404

    drafts = client.get(f"{quiz_url(church.id)}/my-drafts")
    assert drafts.status_code == 200
    assert all(item["id"] != quiz_id for item in drafts.json())


def test_2485b_foreign_church_draft_hidden(db, app, client):
    first = make_church(db, "2485B First Church")
    second = make_church(db, "2485B Second Church")
    creator = make_user(db, "2485B First Admin")
    foreign = make_user(db, "2485B Second Admin")

    add_member(db, first, creator, CHURCH_ROLE_ADMIN)
    add_member(db, second, foreign, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, first, creator)
    assert created.status_code == 201
    quiz_id = created.json()["id"]

    app.state.auth["user"] = foreign

    response = client.get(
        f"{quiz_url(second.id)}/{quiz_id}/author-draft"
    )
    assert response.status_code == 404


def test_2485b_member_cannot_read_author_draft(db, app, client):
    church = make_church(db, "2485B Member Isolation")
    creator = make_user(db, "2485B Admin")
    member = make_user(db, "2485B Member")

    add_member(db, church, creator, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    created = create_quiz(client, app, church, creator)
    assert created.status_code == 201
    quiz_id = created.json()["id"]

    app.state.auth["user"] = member

    response = client.get(
        f"{quiz_url(church.id)}/{quiz_id}/author-draft"
    )
    assert response.status_code == 403


def test_2485b_creator_can_edit_question(db, app, client):
    church = make_church(db, "2485B Editing Church")
    creator = make_user(db, "2485B Editing Admin")
    add_member(db, church, creator, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, church, creator)
    assert created.status_code == 201
    quiz_id = created.json()["id"]

    added = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json=question_payload(),
    )
    assert added.status_code == 201
    question_id = added.json()["id"]

    edited = client.patch(
        f"{quiz_url(church.id)}/{quiz_id}/questions/{question_id}",
        json={
            "question_text": "Who constructed the ark?",
            "correct_option": "B",
        },
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["question_text"] == "Who constructed the ark?"


def test_2485b_other_author_cannot_edit_question(db, app, client):
    church = make_church(db, "2485B Edit Isolation")
    creator = make_user(db, "2485B Edit Creator")
    other = make_user(db, "2485B Edit Other")

    add_member(db, church, creator, CHURCH_ROLE_ADMIN)
    add_member(db, church, other, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, church, creator)
    quiz_id = created.json()["id"]

    added = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json=question_payload(),
    )
    question_id = added.json()["id"]

    app.state.auth["user"] = other

    response = client.patch(
        f"{quiz_url(church.id)}/{quiz_id}/questions/{question_id}",
        json={"question_text": "Unauthorized edit"},
    )

    assert response.status_code == 404
    assert db.get(BibleQuizQuestion, question_id).question_text == \
        "Who built the ark?"


def test_2485b_edit_rejected_after_publish(db, app, client):
    church = make_church(db, "2485B Published Church")
    creator = make_user(db, "2485B Publishing Admin")
    add_member(db, church, creator, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, church, creator)
    quiz_id = created.json()["id"]

    added = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json=question_payload(),
    )
    question_id = added.json()["id"]

    published = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/publish"
    )
    assert published.status_code == 200

    response = client.patch(
        f"{quiz_url(church.id)}/{quiz_id}/questions/{question_id}",
        json={"question_text": "Post-publication edit"},
    )

    assert response.status_code == 409


def test_2485b_rejects_invalid_question_edit(db, app, client):
    church = make_church(db, "2485B Validation Church")
    creator = make_user(db, "2485B Validation Admin")
    add_member(db, church, creator, CHURCH_ROLE_ADMIN)

    created = create_quiz(client, app, church, creator)
    quiz_id = created.json()["id"]

    added = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json=question_payload(),
    )
    question_id = added.json()["id"]

    endpoint = (
        f"{quiz_url(church.id)}/{quiz_id}/questions/{question_id}"
    )

    assert client.patch(
        endpoint,
        json={"question_text": "   "},
    ).status_code == 422

    assert client.patch(
        endpoint,
        json={"correct_option": "Z"},
    ).status_code == 422

    assert client.patch(
        endpoint,
        json={"position": 2},
    ).status_code == 422


def test_2485b_ministry_leader_cannot_publish_reviewed_draft(
    db, app, client
):
    church = make_church(db, "2485B RBAC Church")
    leader = make_user(db, "2485B Ministry Leader")
    add_member(db, church, leader, CHURCH_ROLE_MINISTRY_LEADER)

    created = create_quiz(client, app, church, leader)
    assert created.status_code == 201
    quiz_id = created.json()["id"]

    added = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/questions",
        json=question_payload(),
    )
    assert added.status_code == 201

    response = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/publish"
    )

    assert response.status_code == 403
    assert db.get(BibleQuiz, quiz_id).status == "draft"
