"""
Schemas for trusted XynaFaith persistent-memory integration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


MemoryType = Literal[
    "preference",
    "ministry_context",
    "user_fact",
]


class MemoryCreate(BaseModel):
    memory_type: MemoryType
    key: str
    value: str

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class MemoryUpdate(BaseModel):
    value: str

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class MemoryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: str
    product: str
    memory_type: MemoryType
    key: str
    value: str
    source: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
