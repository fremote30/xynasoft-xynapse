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

CHURCH_INTELLIGENCE_COUNT_KEYS = {
    "members": (
        "active",
    ),
    "ministry": (
        "published_announcements",
        "upcoming_events",
        "published_reading_plans",
        "prayers",
    ),
    "pastoral_care": (
        "active_cases",
        "urgent_cases",
        "overdue_follow_ups",
        "upcoming_follow_ups",
        "unassigned_cases",
    ),
    "groups": (
        "active",
        "ministries",
        "small_groups",
        "service_teams",
        "active_memberships",
    ),
    "operations": (
        "attendance_records",
        "present",
        "absent",
        "excused",
        "upcoming_service_assignments",
        "confirmed_service_assignments",
        "unconfirmed_service_assignments",
    ),
}

CHURCH_INTELLIGENCE_SIGNAL_KEYS = (
    "urgent_care_present",
    "overdue_follow_up_present",
    "unassigned_care_present",
    "upcoming_events_present",
    "active_service_teams_present",
    "service_confirmation_needed",
)


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int) and value >= 0:
        return value

    return None


def _sanitize_church_intelligence(
    value: Any,
) -> dict[str, Any] | None:
    """Allow only bounded aggregate Church Intelligence facts."""
    if not isinstance(value, dict):
        return None

    church_id = value.get("church_id")

    if (
        isinstance(church_id, bool)
        or not isinstance(church_id, int)
        or church_id <= 0
    ):
        return None

    sanitized: dict[str, Any] = {
        "version": 1,
        "church_id": church_id,
    }

    members = value.get("members")
    if not isinstance(members, dict):
        return None

    active = _nonnegative_int(members.get("active"))
    roles = members.get("roles")

    if active is None or not isinstance(roles, dict):
        return None

    safe_roles: dict[str, int] = {}

    for role, count in roles.items():
        safe_count = _nonnegative_int(count)

        if (
            not isinstance(role, str)
            or not role.strip()
            or safe_count is None
        ):
            return None

        safe_roles[role.strip()] = safe_count

    sanitized["members"] = {
        "active": active,
        "roles": safe_roles,
    }

    for section, keys in CHURCH_INTELLIGENCE_COUNT_KEYS.items():
        if section == "members":
            continue

        source = value.get(section)

        if not isinstance(source, dict):
            return None

        target: dict[str, int] = {}

        for key in keys:
            count = _nonnegative_int(source.get(key))

            if count is None:
                return None

            target[key] = count

        sanitized[section] = target

    signals = value.get("signals")

    if not isinstance(signals, dict):
        return None

    safe_signals: dict[str, bool] = {}

    for key in CHURCH_INTELLIGENCE_SIGNAL_KEYS:
        signal = signals.get(key)

        if not isinstance(signal, bool):
            return None

        safe_signals[key] = signal

    sanitized["signals"] = safe_signals

    return sanitized


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
    trusted_context: dict[str, Any]
    history: tuple[ContextMessage, ...]
    memories: tuple[ContextMemory, ...]


def _build_ministry_brief(
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    """Derive bounded attention signals from sanitized intelligence."""
    church_id = intelligence["church_id"]
    pastoral = intelligence["pastoral_care"]
    ministry = intelligence["ministry"]
    operations = intelligence["operations"]

    items: list[dict[str, Any]] = []

    definitions = (
        (
            "urgent_care",
            "urgent",
            pastoral["urgent_cases"],
        ),
        (
            "overdue_follow_up",
            "high",
            pastoral["overdue_follow_ups"],
        ),
        (
            "unassigned_care",
            "high",
            pastoral["unassigned_cases"],
        ),
        (
            "upcoming_follow_up",
            "normal",
            pastoral["upcoming_follow_ups"],
        ),
        (
            "upcoming_event",
            "normal",
            ministry["upcoming_events"],
        ),
        (
            "service_assignment_confirmation",
            "normal",
            operations["unconfirmed_service_assignments"],
        ),
    )

    for item_type, priority, count in definitions:
        if count > 0:
            items.append(
                {
                    "type": item_type,
                    "priority": priority,
                    "count": count,
                }
            )

    attention_count = sum(
        1
        for item in items
        if item["priority"] in {"urgent", "high"}
    )

    return {
        "version": 1,
        "church_id": church_id,
        "items": items,
        "attention_count": attention_count,
    }


def _trusted_product_context(
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    if not context:
        return {}

    trusted: dict[str, Any] = {}

    for key in TRUSTED_CONTEXT_KEYS:
        value = context.get(key)

        if isinstance(value, str):
            normalized = value.strip()

            if normalized:
                trusted[key] = normalized

    church_intelligence = _sanitize_church_intelligence(
        context.get("church_intelligence")
    )

    if church_intelligence is not None:
        trusted["church_intelligence"] = church_intelligence
        trusted["ministry_brief"] = _build_ministry_brief(
            church_intelligence
        )

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
