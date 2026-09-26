from datetime import datetime

from pydantic import BaseModel, Field


class ChurchPrayerCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    category: str | None = Field(default=None, max_length=100)
    is_anonymous: bool = False
    visibility: str = "community"
    recipient_user_ids: list[int] = Field(default_factory=list)
    request_pastoral_care: bool = False


class ChurchPrayerStatusUpdate(BaseModel):
    status: str
    answer_testimony: str | None = Field(default=None, max_length=5000)
    share_testimony: bool = False


class PastoralCareCaseUpdate(BaseModel):
    assigned_to_user_id: int | None = None
    status: str | None = None
    priority: str | None = None
    follow_up_at: datetime | None = None


class PastoralCareNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class TestimonyModerationUpdate(BaseModel):
    status: str
