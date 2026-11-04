"""
XynaFaith V2 ministry intelligence API contracts.

Commercial access, trusted XynAssist identity, quota ownership,
entitlement selection, and usage metrics are server-controlled.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


SermonTransformFormat = Literal[
    "social_post",
    "whatsapp_summary",
    "church_announcement",
    "discussion_questions",
    "sermon_recap",
    "newsletter",
    "devotional",
]


class SavedSermonTransformRequest(BaseModel):
    """
    Transform an authenticated user's persisted sermon.

    Sermon source material is intentionally absent from this contract.
    XynaFaith loads title, scripture, and content from trusted storage.
    """

    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    formats: list[SermonTransformFormat] = Field(
        min_length=1,
        max_length=7,
    )
    audience: str = ""
    tone: str = "balanced"
    denomination: str = "general"
    context: str = ""

    @field_validator("formats")
    @classmethod
    def reject_duplicate_formats(
        cls,
        value: list[SermonTransformFormat],
    ) -> list[SermonTransformFormat]:
        if len(value) != len(set(value)):
            raise ValueError(
                "Content formats must be unique"
            )
        return value


class SavedSermonTransformResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    sermon_id: int
    result: dict[str, Any]
