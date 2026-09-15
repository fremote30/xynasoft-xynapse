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


def test_concurrent_expired_lease_has_one_recovery_owner():
    """
    Two workers racing to recover the same expired processing
    lease must not both become recovery owners.
    """
    from datetime import datetime, timedelta, timezone

    from xynassist_service.db.database import SessionLocal
    from xynassist_service.models.conversation import Conversation
    from xynassist_service.models.conversation_turn import (
        ConversationTurn,
    )
    from xynassist_service.services.turn_idempotency import (
        TurnRequestInProgress,
        claim_turn_request,
    )

    external_user_id = (
        "lease-recovery-user-"
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
            title="Lease recovery concurrency test",
            status="active",
        )
        setup_db.add(conversation)
        setup_db.commit()

        original = claim_turn_request(
            setup_db,
            product="xynafaith",
            external_user_id=external_user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            content="Recover same request",
            context={"source": "test"},
        )

        original_token = original.lease_token

        original.turn.lease_expires_at = (
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        )

        setup_db.commit()
    finally:
        setup_db.close()

    first_recovered = threading.Event()
    allow_first_commit = threading.Event()

    results: dict[str, object] = {}
    errors: list[BaseException] = []

    def first_worker():
        db = SessionLocal()

        try:
            claim = claim_turn_request(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                content="Recover same request",
                context={"source": "test"},
            )

            results["first_token"] = claim.lease_token
            results["first_attempt"] = claim.turn.attempt_count
            first_recovered.set()

            if not allow_first_commit.wait(timeout=10):
                raise RuntimeError(
                    "Timed out waiting to commit recovery"
                )

            db.commit()
            results["first_committed"] = True

        except BaseException as exc:
            errors.append(exc)
            db.rollback()
            first_recovered.set()

        finally:
            db.close()

    def second_worker():
        db = SessionLocal()

        try:
            claim_turn_request(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                content="Recover same request",
                context={"source": "test"},
            )

            results["second_claimed"] = True
            db.commit()

        except TurnRequestInProgress:
            results["second_rejected"] = True
            db.rollback()

        except BaseException as exc:
            errors.append(exc)
            db.rollback()

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

    assert first_recovered.wait(timeout=10), (
        "First worker did not recover expired lease"
    )

    assert errors == []
    assert results["first_token"] != original_token
    assert results["first_attempt"] == 2

    second_thread.start()

    # Worker two must wait on the same PostgreSQL advisory
    # transaction lock while worker one owns recovery.
    time.sleep(0.3)

    assert second_thread.is_alive(), (
        "Second recovery did not wait for advisory lock"
    )

    allow_first_commit.set()

    first_thread.join(timeout=10)
    second_thread.join(timeout=10)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert errors == []

    assert results["first_committed"] is True
    assert results["second_rejected"] is True
    assert "second_claimed" not in results

    verify_db = SessionLocal()

    try:
        rows = (
            verify_db.query(ConversationTurn)
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

        turn = rows[0]

        assert turn.status == "processing"
        assert turn.attempt_count == 2
        assert (
            turn.lease_token
            == results["first_token"]
        )
        assert turn.lease_token != original_token
        assert turn.lease_expires_at is not None

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


def test_recovery_fences_stale_lease_owner():
    """
    After an expired lease is recovered and committed, the
    previous lease owner must be unable to reacquire authority.
    """
    from datetime import datetime, timedelta, timezone

    from xynassist_service.db.database import SessionLocal
    from xynassist_service.models.conversation import Conversation
    from xynassist_service.models.conversation_turn import (
        ConversationTurn,
    )
    from xynassist_service.services.turn_idempotency import (
        TurnLeaseLost,
        claim_turn_request,
        require_turn_lease,
    )

    external_user_id = (
        "lease-fencing-user-"
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
            title="Lease fencing test",
            status="active",
        )
        setup_db.add(conversation)
        setup_db.commit()

        original = claim_turn_request(
            setup_db,
            product="xynafaith",
            external_user_id=external_user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            content="Fence stale worker",
            context={"source": "test"},
        )

        turn_id = original.turn.id
        stale_token = original.lease_token

        original.turn.lease_expires_at = (
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        )

        setup_db.commit()

    finally:
        setup_db.close()

    recovery_db = SessionLocal()

    try:
        recovered = claim_turn_request(
            recovery_db,
            product="xynafaith",
            external_user_id=external_user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            content="Fence stale worker",
            context={"source": "test"},
        )

        current_token = recovered.lease_token

        assert current_token != stale_token
        assert recovered.turn.attempt_count == 2

        recovery_db.commit()

    finally:
        recovery_db.close()

    stale_db = SessionLocal()

    try:
        with pytest.raises(TurnLeaseLost):
            require_turn_lease(
                stale_db,
                product="xynafaith",
                external_user_id=external_user_id,
                request_id=request_id,
                turn_id=turn_id,
                lease_token=stale_token,
            )

        stale_db.rollback()

    finally:
        stale_db.close()

    verify_db = SessionLocal()

    try:
        turn = (
            verify_db.query(ConversationTurn)
            .filter(
                ConversationTurn.id == turn_id
            )
            .one()
        )

        assert turn.status == "processing"
        assert turn.attempt_count == 2
        assert turn.lease_token == current_token
        assert turn.lease_token != stale_token

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
