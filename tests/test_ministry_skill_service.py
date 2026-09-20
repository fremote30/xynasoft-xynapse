from __future__ import annotations

from types import SimpleNamespace

import pytest

import api.services.ministry_skill_service as service
from api.services.xynassist_client import (
    XynAssistConfigurationError,
    XynAssistResponseError,
    XynAssistUnavailableError,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeClient:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = (
            result
            if result is not None
            else {"title": "Grace"}
        )
        self.error = error
        self.calls = []

    async def execute_ministry_skill(
        self,
        *,
        external_user_id,
        skill,
        payload,
    ):
        self.calls.append(
            {
                "external_user_id":
                    external_user_id,
                "skill": skill,
                "payload": payload,
            }
        )

        if self.error is not None:
            raise self.error

        return self.result


@pytest.mark.anyio
async def test_success_reserves_executes_and_consumes(
    monkeypatch,
):
    events = []
    user = SimpleNamespace(id=42)
    client = FakeClient(
        result={
            "title": "Trusting God",
        }
    )

    def fake_reserve(db, **kwargs):
        events.append(
            (
                "reserve",
                kwargs["request_id"],
                kwargs["skill"],
            )
        )

    def fake_consume(db, **kwargs):
        events.append(
            (
                "consume",
                kwargs["request_id"],
            )
        )

    def fake_release(db, **kwargs):
        events.append(
            (
                "release",
                kwargs["request_id"],
            )
        )

    monkeypatch.setattr(
        service,
        "reserve_ministry_skill",
        fake_reserve,
    )
    monkeypatch.setattr(
        service,
        "consume_ministry_skill",
        fake_consume,
    )
    monkeypatch.setattr(
        service,
        "release_ministry_skill",
        fake_release,
    )

    result = await service.execute_ministry_for_user(
        object(),
        user=user,
        request_id="ministry-1",
        skill="sermon.generate",
        payload={
            "input": "Trusting God",
        },
        client=client,
    )

    assert result == {
        "title": "Trusting God",
    }

    assert events == [
        (
            "reserve",
            "ministry-1",
            "sermon.generate",
        ),
        (
            "consume",
            "ministry-1",
        ),
    ]

    assert client.calls == [
        {
            "external_user_id": "42",
            "skill": "sermon.generate",
            "payload": {
                "input": "Trusting God",
            },
        }
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error",
    [
        XynAssistConfigurationError(
            "not configured"
        ),
        XynAssistResponseError(
            "HTTP 422"
        ),
    ],
)
async def test_definite_failure_releases_reservation(
    monkeypatch,
    error,
):
    events = []
    client = FakeClient(error=error)

    monkeypatch.setattr(
        service,
        "reserve_ministry_skill",
        lambda db, **kwargs:
            events.append("reserve"),
    )
    monkeypatch.setattr(
        service,
        "consume_ministry_skill",
        lambda db, **kwargs:
            events.append("consume"),
    )
    monkeypatch.setattr(
        service,
        "release_ministry_skill",
        lambda db, **kwargs:
            events.append("release"),
    )

    with pytest.raises(type(error)):
        await service.execute_ministry_for_user(
            object(),
            user=SimpleNamespace(id=42),
            request_id="ministry-2",
            skill="sermon.generate",
            payload={
                "input": "Grace",
            },
            client=client,
        )

    assert events == [
        "reserve",
        "release",
    ]


@pytest.mark.anyio
async def test_transport_failure_retains_reservation(
    monkeypatch,
):
    events = []

    monkeypatch.setattr(
        service,
        "reserve_ministry_skill",
        lambda db, **kwargs:
            events.append("reserve"),
    )
    monkeypatch.setattr(
        service,
        "consume_ministry_skill",
        lambda db, **kwargs:
            events.append("consume"),
    )
    monkeypatch.setattr(
        service,
        "release_ministry_skill",
        lambda db, **kwargs:
            events.append("release"),
    )

    client = FakeClient(
        error=XynAssistUnavailableError(
            "network failure"
        )
    )

    with pytest.raises(
        service.MinistryExecutionUncertainError
    ):
        await service.execute_ministry_for_user(
            object(),
            user=SimpleNamespace(id=42),
            request_id="ministry-3",
            skill="biblical.research",
            payload={
                "scripture": "Romans 8",
            },
            client=client,
        )

    assert events == [
        "reserve",
    ]


@pytest.mark.anyio
async def test_success_then_consume_failure_never_releases(
    monkeypatch,
):
    events = []

    monkeypatch.setattr(
        service,
        "reserve_ministry_skill",
        lambda db, **kwargs:
            events.append("reserve"),
    )

    def fail_consume(db, **kwargs):
        events.append("consume")
        raise RuntimeError(
            "local persistence failure"
        )

    monkeypatch.setattr(
        service,
        "consume_ministry_skill",
        fail_consume,
    )
    monkeypatch.setattr(
        service,
        "release_ministry_skill",
        lambda db, **kwargs:
            events.append("release"),
    )

    with pytest.raises(
        RuntimeError,
        match="local persistence failure",
    ):
        await service.execute_ministry_for_user(
            object(),
            user=SimpleNamespace(id=42),
            request_id="ministry-4",
            skill="sermon.refine",
            payload={
                "sermon": {
                    "title": "Grace",
                },
                "instruction": "Deepen",
            },
            client=FakeClient(),
        )

    assert events == [
        "reserve",
        "consume",
    ]


@pytest.mark.anyio
async def test_reservation_failure_never_calls_xynassist(
    monkeypatch,
):
    client = FakeClient()

    def fail_reserve(db, **kwargs):
        raise RuntimeError(
            "quota denied"
        )

    monkeypatch.setattr(
        service,
        "reserve_ministry_skill",
        fail_reserve,
    )

    with pytest.raises(
        RuntimeError,
        match="quota denied",
    ):
        await service.execute_ministry_for_user(
            object(),
            user=SimpleNamespace(id=42),
            request_id="ministry-5",
            skill="sermon.generate",
            payload={
                "input": "Grace",
            },
            client=client,
        )

    assert client.calls == []


@pytest.mark.anyio
async def test_authenticated_user_controls_remote_identity(
    monkeypatch,
):
    client = FakeClient()

    monkeypatch.setattr(
        service,
        "reserve_ministry_skill",
        lambda db, **kwargs: None,
    )
    monkeypatch.setattr(
        service,
        "consume_ministry_skill",
        lambda db, **kwargs: None,
    )

    await service.execute_ministry_for_user(
        object(),
        user=SimpleNamespace(id=777),
        request_id="ministry-6",
        skill="biblical.research",
        payload={
            "topic": "grace",
        },
        client=client,
    )

    assert (
        client.calls[0][
            "external_user_id"
        ]
        == "777"
    )
