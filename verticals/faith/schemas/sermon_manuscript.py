from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class ManuscriptSection(BaseModel):
    section_title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=20)
    estimated_minutes: int = Field(..., ge=1, le=60)


class SermonManuscript(BaseModel):
    introduction: str = Field(..., min_length=20)
    body_sections: List[ManuscriptSection] = Field(..., min_length=2)
    application: str = Field(..., min_length=20)
    closing_prayer: str = Field(..., min_length=20)

    estimated_total_minutes: int = Field(..., ge=5, le=120)
    notes_for_pastor: str | None = None


class ManuscriptResponse(BaseModel):
    manuscript: SermonManuscript