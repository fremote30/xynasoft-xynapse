"""
Persistent XynAssist memory services.

Memory access is always scoped to the trusted product-user identity.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from xynassist_service.models.memory import Memory


ALLOWED_MEMORY_TYPES = frozenset(
    {
        "preference",
        "ministry_context",
        "user_fact",
    }
)

ALLOWED_MEMORY_SOURCES = frozenset(
    {
        "explicit_user",
        "system",
    }
)


def _required(value: str, field: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field} is required")

    return normalized


def create_or_update_memory(
    db: Session,
    *,
    external_user_id: str,
    memory_type: str,
    key: str,
    value: str,
    source: str = "explicit_user",
    product: str = "xynafaith",
) -> Memory:
    owner = _required(
        external_user_id,
        "External user identifier",
    )
    product_name = _required(product, "Product")
    kind = _required(memory_type, "Memory type")
    memory_key = _required(key, "Memory key")
    memory_value = _required(value, "Memory value")
    memory_source = _required(source, "Memory source")

    if kind not in ALLOWED_MEMORY_TYPES:
        raise ValueError("Unsupported memory type")

    if memory_source not in ALLOWED_MEMORY_SOURCES:
        raise ValueError("Unsupported memory source")

    memory = (
        db.query(Memory)
        .filter(
            Memory.product == product_name,
            Memory.external_user_id == owner,
            Memory.memory_type == kind,
            Memory.key == memory_key,
        )
        .one_or_none()
    )

    if memory is None:
        memory = Memory(
            product=product_name,
            external_user_id=owner,
            memory_type=kind,
            key=memory_key,
            value=memory_value,
            source=memory_source,
            status="active",
        )
        db.add(memory)
    else:
        memory.value = memory_value
        memory.source = memory_source
        memory.status = "active"

    db.flush()

    return memory


def list_active_memories(
    db: Session,
    *,
    external_user_id: str,
    product: str = "xynafaith",
) -> list[Memory]:
    owner = _required(
        external_user_id,
        "External user identifier",
    )
    product_name = _required(product, "Product")

    return (
        db.query(Memory)
        .filter(
            Memory.product == product_name,
            Memory.external_user_id == owner,
            Memory.status == "active",
        )
        .order_by(
            Memory.memory_type.asc(),
            Memory.key.asc(),
            Memory.id.asc(),
        )
        .all()
    )


def deactivate_memory(
    db: Session,
    *,
    external_user_id: str,
    memory_id: str,
    product: str = "xynafaith",
) -> bool:
    owner = _required(
        external_user_id,
        "External user identifier",
    )
    identifier = _required(memory_id, "Memory identifier")
    product_name = _required(product, "Product")

    memory = (
        db.query(Memory)
        .filter(
            Memory.id == identifier,
            Memory.product == product_name,
            Memory.external_user_id == owner,
        )
        .one_or_none()
    )

    if memory is None:
        return False

    memory.status = "inactive"
    db.flush()

    return True
