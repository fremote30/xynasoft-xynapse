from __future__ import annotations

import os
import uuid

os.environ.setdefault(
    "XYNASSIST_DATABASE_URL",
    "sqlite://",
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from xynassist_service.db.database import Base
from xynassist_service.models.conversation import (
    Conversation,
)
from xynassist_service.models.message import (
    ConversationMessage,
)
from xynassist_service.services.turn_idempotency import (
    TURN_STATUS_COMPLETED,
    TURN_STATUS_FAILED,
    TurnRequestConflict,
    TurnRequestInProgress,
    TurnRequestStateError,
    build_request_fingerprint,
    claim_turn_request,
    complete_turn_request,
    fail_turn_request,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def create_conversation(db, *, user="user-1"):
    conversation = Conversation(
        id=str(uuid.uuid4()),
        product="xynafaith",
        external_user_id=user,
        title="Test",
        status="active",
    )

    db.add(conversation)
    db.commit()

    return conversation


def test_fingerprint_is_stable_for_context_key_order():
    conversation_id = str(uuid.uuid4())

    first = build_request_fingerprint(
        conversation_id=conversation_id,
        content="Hello",
        context={
            "b": 2,
            "a": 1,
        },
    )

    second = build_request_fingerprint(
        conversation_id=conversation_id,
        content="Hello",
        context={
            "a": 1,
            "b": 2,
        },
    )

    assert first == second


def test_new_request_is_claimed(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Hello",
        context=None,
    )

    assert claim.is_replay is False
    assert claim.turn.request_id == request_id
    assert claim.turn.status == "processing"


def test_processing_request_cannot_execute_twice(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Hello",
        context=None,
    )

    with pytest.raises(
        TurnRequestInProgress
    ):
        claim_turn_request(
            db,
            product="xynafaith",
            external_user_id="user-1",
            conversation_id=conversation.id,
            request_id=request_id,
            content="Hello",
            context=None,
        )


def test_completed_request_replays_response(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Hello",
        context={"a": 1},
    )

    user_message = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="user",
        content="Hello",
    )

    assistant_message = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content="Hi",
    )

    db.add_all(
        [
            user_message,
            assistant_message,
        ]
    )
    db.flush()

    response = {
        "skill": "conversation.respond",
        "value": "Hi",
    }

    complete_turn_request(
        db,
        turn=claim.turn,
        response=response,
        user_message_id=user_message.id,
        assistant_message_id=(
            assistant_message.id
        ),
    )

    db.commit()

    replay = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Hello",
        context={"a": 1},
    )

    assert replay.is_replay is True
    assert replay.replay_response == response
    assert (
        replay.turn.status
        == TURN_STATUS_COMPLETED
    )
    assert replay.turn.completed_at is not None


def test_same_request_id_different_content_conflicts(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="First",
        context=None,
    )

    with pytest.raises(
        TurnRequestConflict
    ):
        claim_turn_request(
            db,
            product="xynafaith",
            external_user_id="user-1",
            conversation_id=conversation.id,
            request_id=request_id,
            content="Different",
            context=None,
        )


def test_same_request_id_different_conversation_conflicts(
    db,
):
    first = create_conversation(db)
    second = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=first.id,
        request_id=request_id,
        content="Hello",
        context=None,
    )

    with pytest.raises(
        TurnRequestConflict
    ):
        claim_turn_request(
            db,
            product="xynafaith",
            external_user_id="user-1",
            conversation_id=second.id,
            request_id=request_id,
            content="Hello",
            context=None,
        )


def test_request_id_is_scoped_by_trusted_user(db):
    first = create_conversation(
        db,
        user="user-1",
    )
    second = create_conversation(
        db,
        user="user-2",
    )

    request_id = str(uuid.uuid4())

    first_claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=first.id,
        request_id=request_id,
        content="Hello",
        context=None,
    )

    second_claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-2",
        conversation_id=second.id,
        request_id=request_id,
        content="Hello",
        context=None,
    )

    assert (
        first_claim.turn.id
        != second_claim.turn.id
    )


def test_failed_request_fails_closed(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Hello",
        context=None,
    )

    fail_turn_request(
        db,
        turn=claim.turn,
        error_code="provider_failure",
    )

    db.commit()

    assert (
        claim.turn.status
        == TURN_STATUS_FAILED
    )

    with pytest.raises(
        TurnRequestStateError
    ):
        claim_turn_request(
            db,
            product="xynafaith",
            external_user_id="user-1",
            conversation_id=conversation.id,
            request_id=request_id,
            content="Hello",
            context=None,
        )


def test_invalid_request_id_is_rejected(db):
    conversation = create_conversation(db)

    with pytest.raises(
        ValueError,
        match="request_id must be a UUID",
    ):
        claim_turn_request(
            db,
            product="xynafaith",
            external_user_id="user-1",
            conversation_id=conversation.id,
            request_id="not-a-uuid",
            content="Hello",
            context=None,
        )
