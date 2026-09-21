"""
XynaFaith V2 ministry intelligence API contracts.

Commercial access, trusted XynAssist identity, quota ownership,
entitlement selection, and usage metrics are server-controlled.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


MinistrySkillName = Literal[
    "sermon.generate",
    "sermon.refine",
    "biblical.research",
    "content.transform",
    "sermon.series.generate",
    "bible_study.generate",
    "devotional.generate",
]


class MinistryExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    skill: MinistrySkillName
    input: dict[str, Any]


class MinistryExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    skill: MinistrySkillName
    result: dict[str, Any]
