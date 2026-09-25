"""
Request contracts for XynaFaith V2 Church Space content.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    status: str = "draft"


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    body: str | None = Field(
        default=None,
        min_length=1,
    )
    status: str | None = None


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(
        default=None,
        max_length=255,
    )
    event_url: HttpUrl | None = None
    status: str = "draft"


class EventUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(
        default=None,
        max_length=255,
    )
    event_url: HttpUrl | None = None
    status: str | None = None
