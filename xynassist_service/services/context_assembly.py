"""
Context assembly for Xyniva conversation turns.

This layer combines bounded conversation history, trusted product
context, and owner-scoped persistent memory before invoking Xyniva.

Persistent memory is contextual data, not trusted instruction.
Sensitive pastoral-care records must not be stored or assembled here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from xynassist_service.models.message import ConversationMessage
from xynassist_service.services.memories import list_active_memories


MAX_HISTORY_MESSAGES = 12
MAX_MEMORIES = 20

TRUSTED_CONTEXT_KEYS = (
    "denomination",
    "audience",
    "language",
    "church_name",
)


@dataclass(frozen=True)
class ContextMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ContextMemory:
    memory_type: str
    key: str
    value: str


@dataclass(frozen=True)
class XynivaContextBundle:
    trusted_context: dict[str, str]
    history: tuple[ContextMessage, ...]
    memories: tuple[ContextMemory, ...]


def _trusted_product_context(
    context: dict[str, Any] | None,
) -> dict[str, str]:
    if not context:
        return {}

    trusted: dict[str, str] = {}

    for key in TRUSTED_CONTEXT_KEYS:
        value = context.get(key)

        if isinstance(value, str):
            normalized = value.strip()

            if normalized:
                trusted[key] = normalized

    return trusted


def _bounded_history(
    db: Session,
    *,
    conversation_id: str,
) -> tuple[ContextMessage, ...]:
    """
    Return the most recent persisted messages in chronological order.

    The current user turn is not yet persisted when this function runs,
    so it cannot accidentally duplicate the current request.
    """

    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ConversationMessage.sequence_number.desc(),
        )
        .limit(MAX_HISTORY_MESSAGES)
    )

    newest_first = list(
        db.execute(statement)
        .scalars()
        .all()
    )

    chronological = reversed(newest_first)

    return tuple(
        ContextMessage(
            role=message.role,
            content=message.content,
        )
        for message in chronological
        if message.role in {"user", "assistant"}
        and message.content.strip()
    )


def _bounded_memories(
    db: Session,
    *,
    external_user_id: str,
    product: str,
) -> tuple[ContextMemory, ...]:
    memories = list_active_memories(
        db,
        external_user_id=external_user_id,
        product=product,
        limit=MAX_MEMORIES,
    )

    return tuple(
        ContextMemory(
            memory_type=memory.memory_type,
            key=memory.key,
            value=memory.value,
        )
        for memory in memories
    )


def assemble_xyniva_context(
    db: Session,
    *,
    external_user_id: str,
    conversation_id: str,
    product: str,
    context: dict[str, Any] | None,
) -> XynivaContextBundle:
    return XynivaContextBundle(
        trusted_context=_trusted_product_context(
            context
        ),
        history=_bounded_history(
            db,
            conversation_id=conversation_id,
        ),
        memories=_bounded_memories(
            db,
            external_user_id=external_user_id,
            product=product,
        ),
    )
