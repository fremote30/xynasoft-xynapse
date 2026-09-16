"""
Persistent XynAssist memory services.

Memory access is always scoped to the trusted product-user identity.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import text
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


def _memory_lock_key(
    *,
    product: str,
    external_user_id: str,
    memory_type: str,
    key: str,
) -> int:
    """
    Stable signed 64-bit key for one logical memory identity.

    The namespace prefix prevents accidental overlap with other
    advisory-lock domains that may hash similar identifiers.
    """

    raw = (
        f"xynassist-memory\x1f"
        f"{product}\x1f"
        f"{external_user_id}\x1f"
        f"{memory_type}\x1f"
        f"{key}"
    ).encode("utf-8")

    digest = hashlib.sha256(raw).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=True,
    )


def _lock_memory_identity(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    memory_type: str,
    key: str,
) -> None:
    """
    Serialize writes to one logical memory on PostgreSQL.

    The transaction-scoped lock is released automatically when
    the caller commits or rolls back. Non-PostgreSQL test
    databases intentionally use the database unique constraint
    without advisory locking.
    """

    bind = db.get_bind()

    if bind.dialect.name != "postgresql":
        return

    lock_key = _memory_lock_key(
        product=product,
        external_user_id=external_user_id,
        memory_type=memory_type,
        key=key,
    )

    db.execute(
        text(
            "SELECT pg_advisory_xact_lock(:key)"
        ),
        {"key": lock_key},
    )


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

    _lock_memory_identity(
        db,
        product=product_name,
        external_user_id=owner,
        memory_type=kind,
        key=memory_key,
    )

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
    limit: int | None = None,
) -> list[Memory]:
    owner = _required(
        external_user_id,
        "External user identifier",
    )
    product_name = _required(product, "Product")

    if limit is not None and limit <= 0:
        raise ValueError(
            "Memory limit must be greater than zero"
        )

    query = (
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
    )

    if limit is not None:
        query = query.limit(limit)

    return query.all()


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


def get_active_memory(
    db: Session,
    *,
    external_user_id: str,
    memory_id: str,
    product: str = "xynafaith",
) -> Memory | None:
    owner = _required(
        external_user_id,
        "External user identifier",
    )
    identifier = _required(
        memory_id,
        "Memory identifier",
    )
    product_name = _required(product, "Product")

    return (
        db.query(Memory)
        .filter(
            Memory.id == identifier,
            Memory.product == product_name,
            Memory.external_user_id == owner,
            Memory.status == "active",
        )
        .one_or_none()
    )


def update_memory_value(
    db: Session,
    *,
    external_user_id: str,
    memory_id: str,
    value: str,
    product: str = "xynafaith",
) -> Memory | None:
    memory_value = _required(value, "Memory value")

    memory = get_active_memory(
        db,
        external_user_id=external_user_id,
        memory_id=memory_id,
        product=product,
    )

    if memory is None:
        return None

    memory.value = memory_value
    memory.source = "explicit_user"

    db.flush()

    return memory
