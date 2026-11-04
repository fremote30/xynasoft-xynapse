"""
Real PostgreSQL concurrency tests for persistent XynAssist memory.

Run only with:

    XYNASSIST_RUN_POSTGRES_TESTS=1
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


def test_concurrent_memory_upserts_serialize():
    from xynassist_service.db.database import (
        SessionLocal,
    )
    from xynassist_service.models.memory import Memory
    from xynassist_service.services.memories import (
        create_or_update_memory,
    )

    external_user_id = (
        "memory-concurrency-"
        f"{uuid.uuid4()}"
    )
    memory_type = "preference"
    memory_key = "response_style"

    first_flushed = threading.Event()
    allow_first_commit = threading.Event()

    results: list[tuple[str, str]] = []
    errors: list[BaseException] = []

    def first_worker():
        db = SessionLocal()

        try:
            memory = create_or_update_memory(
                db,
                external_user_id=external_user_id,
                memory_type=memory_type,
                key=memory_key,
                value="concise",
            )

            results.append(
                ("first_flushed", memory.id)
            )
            first_flushed.set()

            if not allow_first_commit.wait(
                timeout=10
            ):
                raise RuntimeError(
                    "Timed out waiting to commit "
                    "first memory transaction"
                )

            db.commit()

            results.append(
                ("first_committed", memory.id)
            )
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
            first_flushed.set()
        finally:
            db.close()

    def second_worker():
        if not first_flushed.wait(timeout=10):
            errors.append(
                RuntimeError(
                    "First memory write never flushed"
                )
            )
            return

        db = SessionLocal()

        try:
            memory = create_or_update_memory(
                db,
                external_user_id=external_user_id,
                memory_type=memory_type,
                key=memory_key,
                value="detailed",
            )

            db.commit()

            results.append(
                ("second_committed", memory.id)
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

    assert first_flushed.wait(
        timeout=10
    ), "First memory write did not flush"

    second_thread.start()

    # Worker two must block on the same transaction-scoped
    # PostgreSQL advisory lock until worker one commits.
    time.sleep(0.3)

    assert second_thread.is_alive(), (
        "Second memory transaction did not wait "
        "for the advisory lock"
    )

    allow_first_commit.set()

    first_thread.join(timeout=10)
    second_thread.join(timeout=10)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert errors == []

    first_ids = [
        memory_id
        for event, memory_id in results
        if event == "first_committed"
    ]
    second_ids = [
        memory_id
        for event, memory_id in results
        if event == "second_committed"
    ]

    assert len(first_ids) == 1
    assert len(second_ids) == 1
    assert second_ids[0] == first_ids[0]

    verify_db = SessionLocal()

    try:
        rows = (
            verify_db.query(Memory)
            .filter(
                Memory.product == "xynafaith",
                Memory.external_user_id
                == external_user_id,
                Memory.memory_type
                == memory_type,
                Memory.key == memory_key,
            )
            .all()
        )

        assert len(rows) == 1
        assert rows[0].id == first_ids[0]
        assert rows[0].status == "active"
        assert rows[0].value == "detailed"
    finally:
        verify_db.close()

    cleanup_db = SessionLocal()

    try:
        cleanup_db.query(Memory).filter(
            Memory.product == "xynafaith",
            Memory.external_user_id
            == external_user_id,
        ).delete(
            synchronize_session=False
        )

        cleanup_db.commit()
    finally:
        cleanup_db.close()
