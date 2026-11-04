"""
Schemas for trusted XynaFaith execution of XynAssist memory actions.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


MemoryActionName = Literal[
    "memory.remember",
    "memory.forget",
]


class MemoryActionExecuteRequest(BaseModel):
    request_id: str
    action_name: MemoryActionName
    arguments: dict[str, Any]

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class MemoryActionExecuteResponse(BaseModel):
    memory_id: str
    memory_type: Literal[
        "preference",
        "ministry_context",
        "user_fact",
    ]
    key: str
    status: Literal[
        "active",
        "inactive",
    ]

    model_config = ConfigDict(
        extra="forbid",
    )
