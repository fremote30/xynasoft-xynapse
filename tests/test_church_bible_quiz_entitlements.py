"""
Bible Quiz entitlement and church RBAC security tests.

Uses isolated SQLite fixtures; never accesses PostgreSQL.
"""

from api.core.church_rbac import (
    CHURCH_ROLE_ADMIN,
    CHURCH_ROLE_MEMBER,
    CHURCH_ROLE_MINISTRY_LEADER,
    MEMBERSHIP_STATUS_ACTIVE,
)
from api.core.entitlements import (
    ENTITLEMENT_BIBLE_QUIZZES,
    ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    ENTITLEMENT_BIBLE_QUIZZES_AI,
)
from api.models.bible_quiz import BibleQuiz
from api.models.church_membership import ChurchMembership

from test_church_bible_quiz_authoring import (
    db,
    app,
    client,
    make_church,
    make_user,
    add_member,
    create_quiz,
    quiz_url,
)


FREE = frozenset({
    ENTITLEMENT_BIBLE_QUIZZES,
})

CHURCH = frozenset({
    ENTITLEMENT_BIBLE_QUIZZES,
    ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
})

CHURCH_PRO = frozenset({
    ENTITLEMENT_BIBLE_QUIZZES,
    ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    ENTITLEMENT_BIBLE_QUIZZES_AI,
})


def set_entitlements(monkeypatch, granted):
    monkeypatch.setattr(
        "api.v1.churches.bible_quiz_router.has_entitlement",
        lambda db, user, entitlement_key, church_id=None: (
            entitlement_key in granted
        ),
    )


def test_free_admin_cannot_create_quiz(
    db, app, client, monkeypatch
):
    church = make_church(db, "Free Admin Church")
    admin = make_user(db, "Free Admin")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    set_entitlements(monkeypatch, FREE)

    response = create_quiz(client, app, church, admin)

    assert response.status_code == 403
    assert db.query(BibleQuiz).count() == 0


def test_church_subscription_allows_authoring(
    db, app, client, monkeypatch
):
    church = make_church(db, "Paid Author Church")
    admin = make_user(db, "Paid Author")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    set_entitlements(monkeypatch, CHURCH)

    response = create_quiz(client, app, church, admin)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "draft"


def test_church_pro_allows_authoring(
    db, app, client, monkeypatch
):
    church = make_church(db, "Pro Author Church")
    admin = make_user(db, "Pro Author")
    add_member(db, church, admin, CHURCH_ROLE_ADMIN)

    set_entitlements(monkeypatch, CHURCH_PRO)

    response = create_quiz(client, app, church, admin)

    assert response.status_code == 201, response.text


def test_paid_member_without_create_permission_is_denied(
    db, app, client, monkeypatch
):
    church = make_church(db, "Paid Member Church")
    member = make_user(db, "Paid Member")
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    set_entitlements(monkeypatch, CHURCH_PRO)

    response = create_quiz(client, app, church, member)

    assert response.status_code == 403
    assert db.query(BibleQuiz).count() == 0


def test_paid_ministry_leader_cannot_publish(
    db, app, client, monkeypatch
):
    church = make_church(db, "Leader Publish Church")
    leader = make_user(db, "Paid Leader")
    add_member(
        db, church, leader, CHURCH_ROLE_MINISTRY_LEADER
    )

    set_entitlements(monkeypatch, CHURCH)

    response = create_quiz(client, app, church, leader)
    assert response.status_code == 201, response.text

    quiz_id = response.json()["id"]

    publish = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/publish"
    )

    assert publish.status_code == 403


def test_free_member_can_list_published_quiz(
    db, app, client, monkeypatch
):
    church = make_church(db, "Free Participation Church")
    admin = make_user(db, "Quiz Publisher")
    member = make_user(db, "Quiz Participant")

    add_member(db, church, admin, CHURCH_ROLE_ADMIN)
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    set_entitlements(monkeypatch, CHURCH)

    created = create_quiz(client, app, church, admin)
    assert created.status_code == 201, created.text

    quiz_id = created.json()["id"]

    question = client.post(
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
    assert question.status_code == 201, question.text

    published = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/publish"
    )
    assert published.status_code == 200, published.text

    set_entitlements(monkeypatch, FREE)
    app.state.auth["user"] = member

    listing = client.get(quiz_url(church.id))
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1

    detail = client.get(
        f"{quiz_url(church.id)}/{quiz_id}"
    )
    assert detail.status_code == 200, detail.text
    assert "correct_option" not in str(detail.json())

    submitted = client.post(
        f"{quiz_url(church.id)}/{quiz_id}/submit",
        json={
            "answers": [
                {
                    "question_id": question.json()["id"],
                    "selected_option": "B",
                }
            ]
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["score"] == 100

    history = client.get(
        f"{quiz_url(church.id)}/my-attempts"
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) == 1


def test_paid_access_does_not_bypass_membership(
    db, app, client, monkeypatch
):
    church = make_church(db, "Membership Gate Church")
    outsider = make_user(db, "Paid Outsider")
    db.commit()

    set_entitlements(monkeypatch, CHURCH_PRO)

    response = create_quiz(client, app, church, outsider)

    assert response.status_code in {403, 404}
    assert db.query(BibleQuiz).count() == 0


def test_paid_access_does_not_bypass_church_isolation(
    db, app, client, monkeypatch
):
    church_a = make_church(db, "Paid Church A")
    church_b = make_church(db, "Paid Church B")
    admin = make_user(db, "Isolated Admin")

    add_member(db, church_a, admin, CHURCH_ROLE_ADMIN)

    set_entitlements(monkeypatch, CHURCH_PRO)

    response = create_quiz(client, app, church_b, admin)

    assert response.status_code == 404
    assert db.query(BibleQuiz).count() == 0


def test_inactive_member_cannot_use_free_quizzes(
    db, app, client, monkeypatch
):
    church = make_church(db, "Inactive Quiz Church")
    member = make_user(db, "Inactive Quiz Member")
    add_member(db, church, member, CHURCH_ROLE_MEMBER)

    membership = db.query(ChurchMembership).filter_by(
        church_id=church.id,
        user_id=member.id,
    ).one()

    membership.status = "suspended"
    db.commit()

    set_entitlements(monkeypatch, FREE)
    app.state.auth["user"] = member

    response = client.get(quiz_url(church.id))

    assert response.status_code in {403, 404}
