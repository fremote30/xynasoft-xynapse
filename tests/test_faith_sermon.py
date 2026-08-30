"""
Characterization tests for the existing XynaFaith sermon API.

These tests intentionally capture the current public contract
before sermon generation is routed through XynAssist.

They must not call external AI providers.
"""

from types import SimpleNamespace

import pytest

from api.core.dependencies import get_current_user


# =========================================================
# Helpers
# =========================================================

def make_user(role: str):
    return SimpleNamespace(
        id=1,
        role=role,
    )


def valid_sermon(
    *,
    scripture: str = "AI scripture",
):
    return {
        "title": "Trust in the Lord",
        "scripture": scripture,
        "introduction": (
            "Trust begins with surrender."
        ),
        "main_points": [
            {
                "title": "Trust God",
                "content": (
                    "Lean on God's wisdom rather "
                    "than your own understanding."
                ),
            }
        ],
        "application": (
            "Choose one area of your life "
            "to surrender to God this week."
        ),
        "conclusion": (
            "Commit your path to the Lord."
        ),
    }


@pytest.fixture()
def override_current_user(client):
    """
    Override XynaFaith authentication for one test.

    Returns a function so each test can choose the role.
    """

    from main import app

    def _override(role: str):
        app.dependency_overrides[
            get_current_user
        ] = lambda: make_user(role)

    yield _override

    app.dependency_overrides.pop(
        get_current_user,
        None,
    )


# =========================================================
# Existing public request/response contract
# =========================================================

def test_generate_sermon_preserves_public_contract(
    client,
    monkeypatch,
    override_current_user,
):
    override_current_user("member")

    captured = {}

    def fake_generate(payload):
        captured["payload"] = payload
        return valid_sermon()

    monkeypatch.setattr(
        "api.routes.faith.generate_ai_response",
        fake_generate,
    )

    response = client.post(
        "/api/v1/faith/sermon",
        json={
            "input": "Trusting God",
            "scripture": "Proverbs 3:5-6",
            "denomination": "pentecostal",
            "audience": "young adults",
            "context": "Sunday service",
            "tone": "encouraging",
            "duration": "30",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert set(data) == {
        "title",
        "scripture",
        "introduction",
        "main_points",
        "application",
        "conclusion",
    }

    assert data["title"] == "Trust in the Lord"
    assert data["scripture"] == "Proverbs 3:5-6"

    assert data["main_points"] == [
        {
            "title": "Trust God",
            "content": (
                "Lean on God's wisdom rather "
                "than your own understanding."
            ),
        }
    ]

    payload = captured["payload"]

    assert payload.input == "Trusting God"
    assert payload.scripture == "Proverbs 3:5-6"
    assert payload.denomination == "pentecostal"
    assert payload.audience == "young adults"
    assert payload.context == "Sunday service"
    assert payload.tone == "encouraging"
    assert payload.duration == "30"


# =========================================================
# Existing defaults
# =========================================================

def test_generate_sermon_preserves_request_defaults(
    client,
    monkeypatch,
    override_current_user,
):
    override_current_user("member")

    captured = {}

    def fake_generate(payload):
        captured["payload"] = payload
        return valid_sermon(
            scripture="",
        )

    monkeypatch.setattr(
        "api.routes.faith.generate_ai_response",
        fake_generate,
    )

    response = client.post(
        "/api/v1/faith/sermon",
        json={
            "input": "Grace",
        },
    )

    assert response.status_code == 200

    payload = captured["payload"]

    assert payload.input == "Grace"
    assert payload.scripture == ""
    assert payload.denomination == "general"
    assert payload.audience == ""
    assert payload.context == ""
    assert payload.tone == "balanced"
    assert payload.duration == "30"


# =========================================================
# Scripture override compatibility behavior
# =========================================================

def test_requested_scripture_overrides_ai_scripture(
    client,
    monkeypatch,
    override_current_user,
):
    override_current_user("pastor")

    def fake_generate(payload):
        return valid_sermon(
            scripture="Different AI scripture",
        )

    monkeypatch.setattr(
        "api.routes.faith.generate_ai_response",
        fake_generate,
    )

    response = client.post(
        "/api/v1/faith/sermon",
        json={
            "input": "Trust",
            "scripture": "Proverbs 3:5-6",
        },
    )

    assert response.status_code == 200

    assert (
        response.json()["scripture"]
        == "Proverbs 3:5-6"
    )


# =========================================================
# Legacy points compatibility
# =========================================================

def test_legacy_points_are_mapped_to_main_points(
    client,
    monkeypatch,
    override_current_user,
):
    override_current_user("member")

    def fake_generate(payload):
        sermon = valid_sermon()
        sermon.pop("main_points")

        sermon["points"] = [
            {
                "title": "Legacy Point",
                "content": "Legacy content",
            }
        ]

        return sermon

    monkeypatch.setattr(
        "api.routes.faith.generate_ai_response",
        fake_generate,
    )

    response = client.post(
        "/api/v1/faith/sermon",
        json={
            "input": "Faith",
        },
    )

    assert response.status_code == 200

    assert response.json()["main_points"] == [
        {
            "title": "Legacy Point",
            "content": "Legacy content",
        }
    ]


# =========================================================
# Existing role authorization
# =========================================================

@pytest.mark.parametrize(
    "role",
    [
        "member",
        "pastor",
        "admin",
    ],
)
def test_supported_roles_can_generate_sermons(
    client,
    monkeypatch,
    override_current_user,
    role,
):
    override_current_user(role)

    monkeypatch.setattr(
        "api.routes.faith.generate_ai_response",
        lambda payload: valid_sermon(),
    )

    response = client.post(
        "/api/v1/faith/sermon",
        json={
            "input": "Grace",
        },
    )

    assert response.status_code == 200


def test_unsupported_role_cannot_generate_sermon(
    client,
    monkeypatch,
    override_current_user,
):
    override_current_user("guest")

    called = False

    def fake_generate(payload):
        nonlocal called
        called = True
        return valid_sermon()

    monkeypatch.setattr(
        "api.routes.faith.generate_ai_response",
        fake_generate,
    )

    response = client.post(
        "/api/v1/faith/sermon",
        json={
            "input": "Grace",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Unauthorized",
    }

    assert called is False
