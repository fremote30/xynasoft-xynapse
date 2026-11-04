from typing import Optional

from pydantic import BaseModel, Field


class ReadingProgressUpdate(BaseModel):
    completed: bool


class MemberSermonNoteCreate(BaseModel):
    sermon_id: Optional[int] = None
    title: Optional[str] = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=50000)


class MemberSermonNoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=50000)
