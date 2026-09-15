from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

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
    TURN_STATUS_PROCESSING,
    TurnLeaseLost,
    TurnRequestConflict,
    TurnRequestInProgress,
    TurnRequestStateError,
    build_request_fingerprint,
    claim_turn_request,
    complete_turn_request,
    fail_turn_request,
    require_turn_lease,
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
        lease_token=claim.lease_token,
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
        lease_token=claim.lease_token,
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


def test_new_request_gets_processing_lease(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Lease me",
        context=None,
    )

    assert claim.is_replay is False
    assert claim.lease_token
    assert (
        claim.turn.lease_token
        == claim.lease_token
    )
    assert claim.turn.lease_expires_at is not None
    assert claim.turn.attempt_count == 1


def test_fresh_processing_lease_cannot_be_stolen(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    first = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Fresh lease",
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
            content="Fresh lease",
            context=None,
        )

    assert first.turn.attempt_count == 1


def test_expired_processing_lease_is_recovered(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    first = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Recover me",
        context={"kind": "lease"},
    )

    old_token = first.lease_token

    first.turn.lease_expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )
    db.commit()

    recovered = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Recover me",
        context={"kind": "lease"},
    )

    assert recovered.is_replay is False
    assert recovered.lease_token
    assert recovered.lease_token != old_token
    assert recovered.turn.attempt_count == 2
    assert (
        recovered.turn.lease_token
        == recovered.lease_token
    )


def test_legacy_processing_without_lease_is_recovered(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Legacy processing",
        context=None,
    )

    claim.turn.lease_token = None
    claim.turn.lease_expires_at = None
    db.commit()

    recovered = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Legacy processing",
        context=None,
    )

    assert recovered.lease_token
    assert recovered.turn.attempt_count == 2


def test_stale_worker_cannot_complete_recovered_turn(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    first = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Fence completion",
        context=None,
    )

    stale_token = first.lease_token

    first.turn.lease_expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )
    db.commit()

    recovered = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Fence completion",
        context=None,
    )
    db.commit()

    db.refresh(recovered.turn)

    with pytest.raises(TurnLeaseLost):
        complete_turn_request(
            db,
            turn=recovered.turn,
            lease_token=stale_token,
            response={"value": "stale"},
            user_message_id=str(uuid.uuid4()),
            assistant_message_id=str(uuid.uuid4()),
        )

    assert (
        recovered.turn.status
        == TURN_STATUS_PROCESSING
    )


def test_stale_worker_cannot_fail_recovered_turn(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    first = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Fence failure",
        context=None,
    )

    stale_token = first.lease_token

    first.turn.lease_expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )
    db.commit()

    recovered = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Fence failure",
        context=None,
    )
    db.commit()

    db.refresh(recovered.turn)

    with pytest.raises(TurnLeaseLost):
        fail_turn_request(
            db,
            turn=recovered.turn,
            lease_token=stale_token,
            error_code="stale_worker",
        )

    assert (
        recovered.turn.status
        == TURN_STATUS_PROCESSING
    )


def test_current_lease_owner_can_complete(db):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Complete lease",
        context=None,
    )

    user_message = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="user",
        content="Complete lease",
    )
    assistant_message = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content="Completed",
    )

    db.add_all(
        [user_message, assistant_message]
    )
    db.flush()

    response = {"value": "Completed"}

    complete_turn_request(
        db,
        turn=claim.turn,
        lease_token=claim.lease_token,
        response=response,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
    )
    db.commit()

    assert (
        claim.turn.status
        == TURN_STATUS_COMPLETED
    )
    assert claim.turn.lease_token is None
    assert claim.turn.lease_expires_at is None

    replay = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Complete lease",
        context=None,
    )

    assert replay.is_replay is True
    assert replay.replay_response == response
    assert replay.lease_token is None


@pytest.mark.parametrize(
    (
        "lease_token_present",
        "lease_expiry_present",
    ),
    [
        (True, False),
        (False, True),
    ],
)
def test_inconsistent_processing_lease_fails_closed(
    db,
    lease_token_present,
    lease_expiry_present,
):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Malformed lease",
        context=None,
    )

    claim.turn.lease_token = (
        str(uuid.uuid4())
        if lease_token_present
        else None
    )
    claim.turn.lease_expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=5)
        if lease_expiry_present
        else None
    )

    db.commit()

    with pytest.raises(
        TurnRequestStateError,
        match="inconsistent lease metadata",
    ):
        claim_turn_request(
            db,
            product="xynafaith",
            external_user_id="user-1",
            conversation_id=conversation.id,
            request_id=request_id,
            content="Malformed lease",
            context=None,
        )


def test_current_owner_can_complete_after_expiry_without_recovery(
    db,
):
    conversation = create_conversation(db)
    request_id = str(uuid.uuid4())

    claim = claim_turn_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        conversation_id=conversation.id,
        request_id=request_id,
        content="Finish after expiry",
        context=None,
    )

    claim.turn.lease_expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )
    db.commit()

    turn = require_turn_lease(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        turn_id=claim.turn.id,
        lease_token=claim.lease_token,
    )

    response = {
        "value": "still current owner",
    }

    complete_turn_request(
        db,
        turn=turn,
        lease_token=claim.lease_token,
        response=response,
        user_message_id=str(uuid.uuid4()),
        assistant_message_id=str(uuid.uuid4()),
    )

    db.commit()
    db.refresh(turn)

    assert turn.status == TURN_STATUS_COMPLETED
    assert turn.lease_token is None
    assert turn.lease_expires_at is None
