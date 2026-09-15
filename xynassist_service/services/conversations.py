"""
Conversation persistence services for XynAssist.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from xynassist_service.models.conversation import (
    Conversation,
)
from xynassist_service.models.message import (
    ConversationMessage,
)


PRODUCT_XYNAFAITH = "xynafaith"


def create_conversation(
    db: Session,
    *,
    external_user_id: str,
    title: str | None,
) -> Conversation:
    conversation = Conversation(
        product=PRODUCT_XYNAFAITH,
        external_user_id=external_user_id,
        title=title,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def list_conversations(
    db: Session,
    *,
    external_user_id: str,
) -> list[Conversation]:
    statement = (
        select(Conversation)
        .where(
            Conversation.product
            == PRODUCT_XYNAFAITH,
            Conversation.external_user_id
            == external_user_id,
        )
        .order_by(
            Conversation.updated_at.desc(),
            Conversation.created_at.desc(),
        )
    )

    return list(
        db.execute(statement)
        .scalars()
        .all()
    )


def get_conversation(
    db: Session,
    *,
    external_user_id: str,
    conversation_id: str,
) -> Conversation | None:
    statement = (
        select(Conversation)
        .where(
            Conversation.id
            == conversation_id,
            Conversation.product
            == PRODUCT_XYNAFAITH,
            Conversation.external_user_id
            == external_user_id,
        )
    )

    return (
        db.execute(statement)
        .scalars()
        .one_or_none()
    )


def list_messages(
    db: Session,
    *,
    conversation_id: str,
) -> list[ConversationMessage]:
    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ConversationMessage.created_at.asc(),
            ConversationMessage.id.asc(),
        )
    )

    return list(
        db.execute(statement)
        .scalars()
        .all()
    )
