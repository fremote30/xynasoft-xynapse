from __future__ import annotations

import os
import uuid

os.environ.setdefault(
    "XYNASSIST_DATABASE_URL",
    "sqlite://",
)
os.environ.setdefault(
    "XYNASSIST_SERVICE_TOKEN",
    "test-service-token",
)

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base, get_db
from xynassist_service.main import app as xynassist_app
from xynassist_service.models.conversation import Conversation
from xynassist_service.models.memory import Memory
from xynassist_service.models.message import ConversationMessage
from xynassist_service.services.turn_engine import TurnEngineResult


def _assign_sqlite_message_sequences(
    session,
    flush_context,
    instances,
):
    pending = [
        obj
        for obj in session.new
        if isinstance(obj, ConversationMessage)
        and obj.sequence_number is None
    ]

    if not pending:
        return

    current = session.execute(
        select(
            func.coalesce(
                func.max(
                    ConversationMessage.sequence_number
                ),
                0,
            )
        )
    ).scalar_one()

    for offset, message in enumerate(
        pending,
        start=1,
    ):
        message.sequence_number = current + offset


@pytest.fixture()
def xynassist_db():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    event.listen(
        OrmSession,
        "before_flush",
        _assign_sqlite_message_sequences,
    )

    session = Session()

    try:
        yield session
    finally:
        event.remove(
            OrmSession,
            "before_flush",
            _assign_sqlite_message_sequences,
        )
        session.close()
        engine.dispose()


@pytest.fixture()
def xynassist_http(
    xynassist_db,
    monkeypatch,
):
    from fastapi.testclient import TestClient

    # XynAssist resolves its service credential lazily at request
    # time. Isolate this test from any developer/production token
    # already present in the shell.
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        "test-service-token",
    )

    def override_db():
        yield xynassist_db

    xynassist_app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(xynassist_app) as client:
            yield client
    finally:
        xynassist_app.dependency_overrides.clear()


def _create_conversation(
    db,
    *,
    user_id: str,
) -> Conversation:
    conversation = Conversation(
        id=str(uuid.uuid4()),
        product="xynafaith",
        external_user_id=user_id,
        title="Memory E2E",
        status="active",
    )

    db.add(conversation)
    db.commit()

    return conversation


def _active_memories(
    db,
    *,
    user_id: str,
):
    db.expire_all()

    return db.execute(
        select(Memory)
        .where(
            Memory.product == "xynafaith",
            Memory.external_user_id == user_id,
            Memory.status == "active",
        )
        .order_by(Memory.key)
    ).scalars().all()


def test_memory_lifecycle_crosses_real_xynassist_boundaries(
    xynassist_db,
    xynassist_http,
    monkeypatch,
):
    """
    Full XynAssist-side memory lifecycle.

    This deliberately uses the real trusted HTTP routes and durable
    services while keeping model behavior deterministic.
    """

    from xynassist_service.services import turns

    user_id = "memory-e2e-user"
    conversation = _create_conversation(
        xynassist_db,
        user_id=user_id,
    )

    observed_bundles = []
    phase = {"value": "remember"}

    def deterministic_engine(
        *,
        content,
        context,
        context_bundle=None,
    ):
        observed_bundles.append(context_bundle)

        if phase["value"] == "remember":
            return TurnEngineResult(
                content="I will remember that.",
                skill="memory.remember",
                action={
                    "name": "memory.remember",
                    "arguments": {
                        "memory_type": "preference",
                        "key": "preferred_sermon_length",
                        "value": "25 minutes",
                    },
                },
            )

        if phase["value"] == "recall":
            return TurnEngineResult(
                content="Your preferred sermon length is 25 minutes.",
                skill="conversation.respond",
            )

        if phase["value"] == "forget_proposal":
            return TurnEngineResult(
                content="I can forget that preference.",
                skill="memory.forget",
                action={
                    "name": "memory.forget",
                    "arguments": {
                        "memory_type": "preference",
                        "key": "preferred_sermon_length",
                    },
                },
                prompt="Should I forget that preference?",
            )

        if phase["value"] == "decline":
            return TurnEngineResult(
                content="Understood. I will keep it.",
                skill="conversation.respond",
            )

        if phase["value"] == "confirm":
            return TurnEngineResult(
                content="Confirmed.",
                skill="conversation.confirm",
                confirmation={
                    "action_name": "memory.forget",
                },
            )

        raise AssertionError(
            f"Unexpected phase: {phase['value']}"
        )

    monkeypatch.setattr(
        turns,
        "execute_turn_engine",
        deterministic_engine,
    )

    headers = {
        "X-XynAssist-Service-Token":
            "test-service-token",
        "X-XynAssist-External-User-Id":
            user_id,
    }

    client = xynassist_http

    if client is None:
        raise AssertionError("XynAssist test client is unavailable")

        phase["value"] = "remember"

        remember_turn = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                f"conversations/{conversation.id}/turns"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "content": (
                    "Remember that I prefer "
                    "25-minute sermons."
                ),
            },
        )

        assert remember_turn.status_code == 200

        remember_payload = remember_turn.json()

        assert remember_payload["action"]["name"] == (
            "memory.remember"
        )

        action_request_id = str(uuid.uuid4())

        remember_execution = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                "memory-actions/execute"
            ),
            headers=headers,
            json={
                "request_id": action_request_id,
                "action_name": "memory.remember",
                "arguments": (
                    remember_payload["action"]["arguments"]
                ),
            },
        )

        assert remember_execution.status_code == 200

        memories = _active_memories(
            xynassist_db,
            user_id=user_id,
        )

        assert len(memories) == 1
        assert memories[0].key == (
            "preferred_sermon_length"
        )
        assert memories[0].value == "25 minutes"

        # Exact retry must replay rather than duplicate mutation.
        remember_replay = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                "memory-actions/execute"
            ),
            headers=headers,
            json={
                "request_id": action_request_id,
                "action_name": "memory.remember",
                "arguments": (
                    remember_payload["action"]["arguments"]
                ),
            },
        )

        assert remember_replay.status_code == 200
        assert remember_replay.json() == (
            remember_execution.json()
        )

        assert len(
            _active_memories(
                xynassist_db,
                user_id=user_id,
            )
        ) == 1

        phase["value"] = "recall"

        recall_turn = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                f"conversations/{conversation.id}/turns"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "content": (
                    "What sermon length do I prefer?"
                ),
            },
        )

        assert recall_turn.status_code == 200

        recall_bundle = observed_bundles[-1]

        assert recall_bundle is not None
        assert any(
            memory.key == "preferred_sermon_length"
            and memory.value == "25 minutes"
            for memory in recall_bundle.memories
        )

        phase["value"] = "forget_proposal"

        forget_turn = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                f"conversations/{conversation.id}/turns"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "content": (
                    "Forget my sermon length preference."
                ),
            },
        )

        assert forget_turn.status_code == 200
        forget_payload = forget_turn.json()

        assert forget_payload["action"]["name"] == (
            "memory.forget"
        )
        assert forget_payload["prompt"]

        # No trusted confirmation header: destructive action fails closed.
        denied_forget = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                "memory-actions/execute"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "action_name": "memory.forget",
                "arguments": (
                    forget_payload["action"]["arguments"]
                ),
            },
        )

        assert denied_forget.status_code in {
            400,
            409,
            422,
        }

        assert len(
            _active_memories(
                xynassist_db,
                user_id=user_id,
            )
        ) == 1

        # A negative reply is a response, never trusted deletion.
        phase["value"] = "decline"

        decline_turn = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                f"conversations/{conversation.id}/turns"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "content": "No, keep it.",
                "context": {
                    "pending_memory_action":
                        "memory.forget",
                },
            },
        )

        assert decline_turn.status_code == 200
        assert decline_turn.json().get(
            "confirmation"
        ) is None

        assert len(
            _active_memories(
                xynassist_db,
                user_id=user_id,
            )
        ) == 1

        # A later trusted affirmative confirmation can execute.
        phase["value"] = "confirm"

        confirm_turn = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                f"conversations/{conversation.id}/turns"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "content": "Yes, forget it.",
                "context": {
                    "pending_memory_action":
                        "memory.forget",
                },
            },
        )

        assert confirm_turn.status_code == 200
        assert confirm_turn.json()["confirmation"] == {
            "action_name": "memory.forget",
        }

        confirmed_headers = dict(headers)
        confirmed_headers[
            "X-XynAssist-Action-Confirmed"
        ] = "true"

        forget_execution = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                "memory-actions/execute"
            ),
            headers=confirmed_headers,
            json={
                "request_id": str(uuid.uuid4()),
                "action_name": "memory.forget",
                "arguments": (
                    forget_payload["action"]["arguments"]
                ),
            },
        )

        assert forget_execution.status_code == 200

        assert _active_memories(
            xynassist_db,
            user_id=user_id,
        ) == []

        phase["value"] = "recall"

        after_forget = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                f"conversations/{conversation.id}/turns"
            ),
            headers=headers,
            json={
                "request_id": str(uuid.uuid4()),
                "content": (
                    "What sermon length do I prefer?"
                ),
            },
        )

        assert after_forget.status_code == 200

        final_bundle = observed_bundles[-1]

        assert final_bundle is not None
        assert all(
            memory.key != "preferred_sermon_length"
            for memory in final_bundle.memories
        )


def test_memory_isolation_between_users(
    xynassist_db,
    xynassist_http,
):
    owner = "memory-owner"
    other = "memory-other"

    owner_headers = {
        "X-XynAssist-Service-Token":
            "test-service-token",
        "X-XynAssist-External-User-Id":
            owner,
    }

    other_headers = {
        "X-XynAssist-Service-Token":
            "test-service-token",
        "X-XynAssist-External-User-Id":
            other,
    }

    client = xynassist_http

    if client is None:
        raise AssertionError("XynAssist test client is unavailable")

        created = client.post(
            (
                "/api/v1/integrations/xynafaith/"
                "memory-actions/execute"
            ),
            headers=owner_headers,
            json={
                "request_id": str(uuid.uuid4()),
                "action_name": "memory.remember",
                "arguments": {
                    "memory_type": "preference",
                    "key": "preferred_sermon_length",
                    "value": "25 minutes",
                },
            },
        )

        assert created.status_code == 200

        other_memories = client.get(
            (
                "/api/v1/integrations/xynafaith/"
                "memories"
            ),
            headers=other_headers,
        )

        assert other_memories.status_code == 200
        assert other_memories.json() == []

        owner_memories = client.get(
            (
                "/api/v1/integrations/xynafaith/"
                "memories"
            ),
            headers=owner_headers,
        )

        assert owner_memories.status_code == 200
        assert len(owner_memories.json()) == 1


def test_xynafaith_outer_route_owns_trusted_forget_confirmation(
    xynassist_db,
    xynassist_http,
    monkeypatch,
):
    """
    Prove the complete trust boundary:

    browser -> XynaFaith -> XynAssist -> structured confirmation
    -> XynaFaith durable pending state -> trusted memory deletion.

    The browser never supplies the trusted confirmation header.
    """

    from unittest.mock import Mock

    from fastapi.testclient import TestClient

    from api.core.dependencies import (
        get_current_user,
        get_db as faith_get_db,
    )
    from main import app as faith_app
    from api.models.user import User
    from api.services.xynassist_client import XynAssistClient
    from xynassist_service.services import turns

    user = Mock(spec=User)
    user.id = 456

    faith_db = Mock()

    conversation = _create_conversation(
        xynassist_db,
        user_id=str(user.id),
    )

    phase = {"value": "forget_proposal"}

    def deterministic_engine(
        *,
        content,
        context,
        context_bundle=None,
    ):
        if phase["value"] == "forget_proposal":
            return TurnEngineResult(
                content="I can forget that preference.",
                skill="memory.forget",
                action={
                    "name": "memory.forget",
                    "arguments": {
                        "memory_type": "preference",
                        "key": "preferred_sermon_length",
                    },
                },
                prompt="Should I forget that preference?",
            )

        if phase["value"] == "confirm":
            assert context == {
                "pending_memory_action":
                    "memory.forget",
            }

            return TurnEngineResult(
                content="Confirmed.",
                skill="conversation.confirm",
                confirmation={
                    "action_name": "memory.forget",
                },
            )

        raise AssertionError(
            f"Unexpected phase: {phase['value']}"
        )

    monkeypatch.setattr(
        turns,
        "execute_turn_engine",
        deterministic_engine,
    )

    # Seed the actual XynAssist memory through its trusted route.
    seed = xynassist_http.post(
        (
            "/api/v1/integrations/xynafaith/"
            "memory-actions/execute"
        ),
        headers={
            "X-XynAssist-Service-Token":
                "test-service-token",
            "X-XynAssist-External-User-Id":
                str(user.id),
        },
        json={
            "request_id": str(uuid.uuid4()),
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "preferred_sermon_length",
                "value": "25 minutes",
            },
        },
    )

    assert seed.status_code == 200

    pending_state = {"value": None}

    class Pending:
        action_name = "memory.forget"
        memory_type = "preference"
        memory_key = "preferred_sermon_length"
        source_message_id = ""
        action_request_id = ""

    def get_pending_memory_forget(
        *,
        db,
        user_id,
        conversation_id,
    ):
        assert db is faith_db
        assert user_id == user.id
        assert conversation_id == conversation.id
        return pending_state["value"]

    def record_pending_memory_forget(
        *,
        db,
        user_id,
        conversation_id,
        memory_type,
        memory_key,
        source_message_id,
        action_request_id,
    ):
        assert db is faith_db
        assert user_id == user.id
        assert conversation_id == conversation.id

        pending = Pending()
        pending.memory_type = memory_type
        pending.memory_key = memory_key
        pending.source_message_id = source_message_id
        pending.action_request_id = action_request_id

        pending_state["value"] = pending
        return pending

    def consume_pending_memory_forget(
        *,
        db,
        pending,
    ):
        assert db is faith_db
        assert pending is pending_state["value"]
        pending_state["value"] = None

    class BridgedXynAssistClient:
        async def execute_conversation_turn(
            self,
            *,
            external_user_id,
            conversation_id,
            request_id,
            content,
            context=None,
        ):
            headers = {
                "X-XynAssist-Service-Token":
                    "test-service-token",
                "X-XynAssist-External-User-Id":
                    external_user_id,
            }

            body = {
                "request_id": request_id,
                "content": content,
            }

            if context is not None:
                body["context"] = context

            response = xynassist_http.post(
                (
                    "/api/v1/integrations/xynafaith/"
                    f"conversations/{conversation_id}/turns"
                ),
                headers=headers,
                json=body,
            )

            response.raise_for_status()
            return response.json()

        async def execute_memory_action(
            self,
            *,
            external_user_id,
            request_id,
            action_name,
            arguments,
            trusted_confirmed=False,
        ):
            headers = {
                "X-XynAssist-Service-Token":
                    "test-service-token",
                "X-XynAssist-External-User-Id":
                    external_user_id,
            }

            if trusted_confirmed is True:
                headers[
                    "X-XynAssist-Action-Confirmed"
                ] = "true"

            response = xynassist_http.post(
                (
                    "/api/v1/integrations/xynafaith/"
                    "memory-actions/execute"
                ),
                headers=headers,
                json={
                    "request_id": request_id,
                    "action_name": action_name,
                    "arguments": arguments,
                },
            )

            response.raise_for_status()
            return response.json()

    monkeypatch.setattr(
        "api.routes.faith_conversations.XynAssistClient",
        BridgedXynAssistClient,
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        get_pending_memory_forget,
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_memory_forget",
        record_pending_memory_forget,
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_pending_memory_forget",
        consume_pending_memory_forget,
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "reserve_conversation_turn",
        Mock(),
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_conversation_turn",
        Mock(),
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "release_conversation_turn",
        Mock(),
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XYNASSIST_ENABLED",
        True,
    )

    faith_app.dependency_overrides[
        get_current_user
    ] = lambda: user

    faith_app.dependency_overrides[
        faith_get_db
    ] = lambda: faith_db

    try:
        with TestClient(faith_app) as client:
            proposal = client.post(
                (
                    "/api/v1/faith/conversations/"
                    f"{conversation.id}/turns"
                ),
                json={
                    "request_id": str(uuid.uuid4()),
                    "content": (
                        "Forget my sermon length preference."
                    ),
                },
            )

            assert proposal.status_code == 200
            assert pending_state["value"] is not None

            stable_action_request_id = (
                pending_state["value"].action_request_id
            )

            assert stable_action_request_id

            # Proposal alone cannot mutate the memory.
            assert len(
                _active_memories(
                    xynassist_db,
                    user_id=str(user.id),
                )
            ) == 1

            phase["value"] = "confirm"

            confirmation = client.post(
                (
                    "/api/v1/faith/conversations/"
                    f"{conversation.id}/turns"
                ),
                json={
                    "request_id": str(uuid.uuid4()),
                    "content": "Yes, forget it.",
                },
            )

            assert confirmation.status_code == 200

    finally:
        faith_app.dependency_overrides.clear()

    # XynaFaith consumed pending state only after successful
    # trusted XynAssist execution.
    assert pending_state["value"] is None

    # The XynAssist-owned memory was actually deactivated.
    assert _active_memories(
        xynassist_db,
        user_id=str(user.id),
    ) == []

    # The stable pending action identity, not the later chat-turn
    # request ID, must be the destructive action execution identity.
    from xynassist_service.models.action_execution import (
        ActionExecution,
    )

    xynassist_db.expire_all()

    execution = xynassist_db.execute(
        select(ActionExecution).where(
            ActionExecution.external_user_id
            == str(user.id),
            ActionExecution.action_name
            == "memory.forget",
        )
    ).scalar_one()

    assert execution.request_id == stable_action_request_id
