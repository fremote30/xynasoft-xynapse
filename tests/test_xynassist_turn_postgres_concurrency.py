"""
Real PostgreSQL concurrency tests for XynAssist turn idempotency.

Run only with:

    XYNASSIST_RUN_POSTGRES_TESTS=1

The test proves that concurrent claims for the same trusted
request_id cannot both proceed to AI execution.
"""

from __future__ import annotations

import os
import threading
import time
import uuid

import pytest

RUN_POSTGRES = (
    os.getenv("XYNASSIST_RUN_POSTGRES_TESTS")
    == "1"
)

pytestmark = pytest.mark.skipif(
    not RUN_POSTGRES,
    reason=(
        "Set XYNASSIST_RUN_POSTGRES_TESTS=1 "
        "to run PostgreSQL integration tests"
    ),
)


def test_concurrent_same_request_has_one_winner():
    from xynassist_service.db.database import (
        SessionLocal,
    )
    from xynassist_service.models.conversation import (
        Conversation,
    )
    from xynassist_service.models.conversation_turn import (
        ConversationTurn,
    )
    from xynassist_service.services.turn_idempotency import (
        TurnRequestInProgress,
        claim_turn_request,
    )

    external_user_id = (
        "concurrency-user-"
        f"{uuid.uuid4()}"
    )
    conversation_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    setup_db = SessionLocal()

    try:
        conversation = Conversation(
            id=conversation_id,
            product="xynafaith",
            external_user_id=external_user_id,
            title="Concurrency test",
            status="active",
        )
        setup_db.add(conversation)
        setup_db.commit()
    finally:
        setup_db.close()

    first_claimed = threading.Event()
    allow_first_commit = threading.Event()

    results: list[str] = []
    errors: list[BaseException] = []

    def first_worker():
        db = SessionLocal()

        try:
            claim_turn_request(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                content="Same request",
                context={"source": "test"},
            )

            results.append("first_claimed")
            first_claimed.set()

            if not allow_first_commit.wait(
                timeout=10
            ):
                raise RuntimeError(
                    "Timed out waiting to commit "
                    "first transaction"
                )

            db.commit()
            results.append("first_committed")
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
            first_claimed.set()
        finally:
            db.close()

    def second_worker():
        if not first_claimed.wait(timeout=10):
            errors.append(
                RuntimeError(
                    "First worker never claimed request"
                )
            )
            return

        db = SessionLocal()

        try:
            claim_turn_request(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                content="Same request",
                context={"source": "test"},
            )

            db.commit()
            results.append(
                "second_unexpectedly_claimed"
            )
        except TurnRequestInProgress:
            db.rollback()
            results.append(
                "second_rejected"
            )
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()

    first_thread = threading.Thread(
        target=first_worker,
        daemon=True,
    )

    second_thread = threading.Thread(
        target=second_worker,
        daemon=True,
    )

    first_thread.start()

    assert first_claimed.wait(
        timeout=10
    ), "First claim did not complete"

    second_thread.start()

    # Give worker two time to reach the PostgreSQL advisory
    # lock. It must not complete while worker one still owns
    # the transaction-scoped lock.
    time.sleep(0.3)

    assert second_thread.is_alive(), (
        "Second transaction did not wait "
        "for the request advisory lock"
    )

    allow_first_commit.set()

    first_thread.join(timeout=10)
    second_thread.join(timeout=10)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert errors == []

    assert "first_claimed" in results
    assert "first_committed" in results
    assert "second_rejected" in results

    assert (
        "second_unexpectedly_claimed"
        not in results
    )

    verify_db = SessionLocal()

    try:
        rows = (
            verify_db.query(
                ConversationTurn
            )
            .filter(
                ConversationTurn.product
                == "xynafaith",
                ConversationTurn.external_user_id
                == external_user_id,
                ConversationTurn.request_id
                == request_id,
            )
            .all()
        )

        assert len(rows) == 1
        assert rows[0].status == "processing"
    finally:
        verify_db.close()

    cleanup_db = SessionLocal()

    try:
        cleanup_db.query(
            ConversationTurn
        ).filter(
            ConversationTurn.external_user_id
            == external_user_id
        ).delete(
            synchronize_session=False
        )

        cleanup_db.query(
            Conversation
        ).filter(
            Conversation.external_user_id
            == external_user_id
        ).delete(
            synchronize_session=False
        )

        cleanup_db.commit()
    finally:
        cleanup_db.close()
