from __future__ import annotations

import os

os.environ.setdefault(
    "XYNASSIST_DATABASE_URL",
    "sqlite://",
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
from xynassist_service.services.memories import (
    create_or_update_memory,
    deactivate_memory,
    list_active_memories,
)


def make_session():
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

    return engine, Session()


def test_create_and_list_memory():
    engine, db = make_session()

    try:
        memory = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="preference",
            key="response_style",
            value="concise",
        )

        db.commit()

        memories = list_active_memories(
            db,
            external_user_id="user-1",
        )

        assert len(memories) == 1
        assert memories[0].id == memory.id
        assert memories[0].memory_type == "preference"
        assert memories[0].key == "response_style"
        assert memories[0].value == "concise"
        assert memories[0].source == "explicit_user"
        assert memories[0].status == "active"
    finally:
        db.close()
        engine.dispose()


def test_update_reuses_same_memory_record():
    engine, db = make_session()

    try:
        first = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="ministry_context",
            key="denomination",
            value="Baptist",
        )

        first_id = first.id
        db.commit()

        second = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="ministry_context",
            key="denomination",
            value="Methodist",
        )

        db.commit()

        memories = list_active_memories(
            db,
            external_user_id="user-1",
        )

        assert second.id == first_id
        assert len(memories) == 1
        assert memories[0].value == "Methodist"
    finally:
        db.close()
        engine.dispose()


def test_memories_are_owner_scoped():
    engine, db = make_session()

    try:
        first = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="preference",
            key="language",
            value="English",
        )

        second = create_or_update_memory(
            db,
            external_user_id="user-2",
            memory_type="preference",
            key="language",
            value="Twi",
        )

        db.commit()

        first_memories = list_active_memories(
            db,
            external_user_id="user-1",
        )

        second_memories = list_active_memories(
            db,
            external_user_id="user-2",
        )

        assert [item.id for item in first_memories] == [
            first.id
        ]

        assert [item.id for item in second_memories] == [
            second.id
        ]
    finally:
        db.close()
        engine.dispose()


def test_memories_are_product_scoped():
    engine, db = make_session()

    try:
        faith = create_or_update_memory(
            db,
            external_user_id="shared-user",
            product="xynafaith",
            memory_type="preference",
            key="language",
            value="English",
        )

        legal = create_or_update_memory(
            db,
            external_user_id="shared-user",
            product="xynalegal",
            memory_type="preference",
            key="language",
            value="French",
        )

        db.commit()

        faith_memories = list_active_memories(
            db,
            external_user_id="shared-user",
            product="xynafaith",
        )

        legal_memories = list_active_memories(
            db,
            external_user_id="shared-user",
            product="xynalegal",
        )

        assert [item.id for item in faith_memories] == [
            faith.id
        ]

        assert [item.id for item in legal_memories] == [
            legal.id
        ]
    finally:
        db.close()
        engine.dispose()


def test_deactivate_is_owner_scoped():
    engine, db = make_session()

    try:
        memory = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="user_fact",
            key="preferred_bible_translation",
            value="NIV",
        )

        db.commit()

        changed = deactivate_memory(
            db,
            external_user_id="user-2",
            memory_id=memory.id,
        )

        assert changed is False

        db.commit()

        owner_memories = list_active_memories(
            db,
            external_user_id="user-1",
        )

        assert len(owner_memories) == 1

        changed = deactivate_memory(
            db,
            external_user_id="user-1",
            memory_id=memory.id,
        )

        assert changed is True

        db.commit()

        owner_memories = list_active_memories(
            db,
            external_user_id="user-1",
        )

        assert owner_memories == []
    finally:
        db.close()
        engine.dispose()


def test_reactivating_memory_preserves_identity():
    engine, db = make_session()

    try:
        memory = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="preference",
            key="response_style",
            value="concise",
        )

        memory_id = memory.id
        db.commit()

        assert deactivate_memory(
            db,
            external_user_id="user-1",
            memory_id=memory_id,
        )

        db.commit()

        restored = create_or_update_memory(
            db,
            external_user_id="user-1",
            memory_type="preference",
            key="response_style",
            value="detailed",
        )

        db.commit()

        assert restored.id == memory_id
        assert restored.status == "active"
        assert restored.value == "detailed"
    finally:
        db.close()
        engine.dispose()


def test_invalid_memory_type_is_rejected():
    engine, db = make_session()

    try:
        try:
            create_or_update_memory(
                db,
                external_user_id="user-1",
                memory_type="pastoral_care",
                key="confidential_note",
                value="Sensitive information",
            )
        except ValueError as exc:
            assert str(exc) == "Unsupported memory type"
        else:
            raise AssertionError(
                "Sensitive memory type was accepted"
            )
    finally:
        db.close()
        engine.dispose()


def test_blank_memory_value_is_rejected():
    engine, db = make_session()

    try:
        try:
            create_or_update_memory(
                db,
                external_user_id="user-1",
                memory_type="preference",
                key="language",
                value="   ",
            )
        except ValueError as exc:
            assert str(exc) == "Memory value is required"
        else:
            raise AssertionError(
                "Blank memory value was accepted"
            )
    finally:
        db.close()
        engine.dispose()
