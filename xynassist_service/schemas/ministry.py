"""
Trusted XynaFaith -> XynAssist ministry execution contracts.

XynaFaith supplies user identity through trusted integration headers.
The request body may select only a supported ministry skill and provide
that skill's typed input payload.
"""

from __future__ import annotations

from typing import Any, Literal

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

    skill: MinistrySkillName
    input: dict[str, Any]


class MinistryExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: MinistrySkillName
    result: dict[str, Any]
