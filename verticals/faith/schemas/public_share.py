# verticals/faith/schemas/public_share.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from verticals.faith.schemas.sermon_input import SermonInput
from verticals.faith.schemas.sermon_output import SermonOutput
from verticals.faith.schemas.sermon_manuscript import ManuscriptResponse


class PublishSermonRequest(BaseModel):
    sermon_input: SermonInput
    sermon_output: SermonOutput
    manuscript: Optional[ManuscriptResponse] = None


class PublishSermonResponse(BaseModel):
    share_id: str
    share_path: str
    share_url: str


class PublicSermonResponse(BaseModel):
    share_id: str
    title: str
    created_at: str
    payload_input: dict
    payload_output: dict
    payload_manuscript: Optional[dict] = None
    questions_count: int = 0


class MemberQuestionRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    question: str = Field(..., min_length=2, max_length=2000)


class MemberQuestionResponse(BaseModel):
    ok: bool = True
    question_id: int