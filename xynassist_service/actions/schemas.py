"""
Typed argument contracts for XynAssist action proposals.

These schemas validate proposal structure only. They do not
authorize or execute mutations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)


MemoryType = Literal[
    "preference",
    "ministry_context",
    "user_fact",
]


class _MemoryActionBase(BaseModel):
    memory_type: MemoryType
    key: str

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("key")
    @classmethod
    def validate_key(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Memory key is required"
            )

        return value


class RememberMemoryArguments(
    _MemoryActionBase,
):
    value: str

    @field_validator("value")
    @classmethod
    def validate_value(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Memory value is required"
            )

        return value


class ForgetMemoryArguments(
    _MemoryActionBase,
):
    pass
