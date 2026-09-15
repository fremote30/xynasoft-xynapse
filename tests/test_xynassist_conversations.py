from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
from xynassist_service.models import (
    Conversation,
    ConversationMessage,
)
from xynassist_service.services.conversations import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
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

    return Session()


def test_create_and_get_conversation():
    db = make_session()

    try:
        created = create_conversation(
            db,
            external_user_id="123",
            title="Sunday sermon",
        )

        found = get_conversation(
            db,
            external_user_id="123",
            conversation_id=created.id,
        )

        assert found is not None
        assert found.id == created.id
        assert found.product == "xynafaith"
        assert found.external_user_id == "123"
        assert found.title == "Sunday sermon"
        assert found.status == "active"
    finally:
        db.close()


def test_conversation_is_owner_scoped():
    db = make_session()

    try:
        created = create_conversation(
            db,
            external_user_id="123",
            title="Private conversation",
        )

        found = get_conversation(
            db,
            external_user_id="456",
            conversation_id=created.id,
        )

        assert found is None
    finally:
        db.close()


def test_list_conversations_is_owner_scoped():
    db = make_session()

    try:
        create_conversation(
            db,
            external_user_id="123",
            title="One",
        )

        create_conversation(
            db,
            external_user_id="123",
            title="Two",
        )

        create_conversation(
            db,
            external_user_id="456",
            title="Other",
        )

        conversations = list_conversations(
            db,
            external_user_id="123",
        )

        assert len(conversations) == 2
        assert {
            item.title
            for item in conversations
        } == {
            "One",
            "Two",
        }
    finally:
        db.close()


def test_messages_are_ordered_and_scoped_to_conversation():
    from datetime import datetime, timedelta, timezone

    db = make_session()

    try:
        conversation = create_conversation(
            db,
            external_user_id="123",
            title="Sunday sermon",
        )

        first_time = datetime(
            2026,
            9,
            14,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        )

        second_time = first_time + timedelta(
            seconds=1
        )

        first = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content="Hello",
            skill="conversation",
            created_at=first_time,
        )

        second = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content="Hi",
            skill="conversation",
            created_at=second_time,
        )

        db.add_all([
            second,
            first,
        ])
        db.commit()

        messages = list_messages(
            db,
            conversation_id=conversation.id,
        )

        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi"
    finally:
        db.close()
