from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PrayerRecipientCreate(BaseModel):
    user_id: int
    role: Optional[str] = None


class PrayerCreate(BaseModel):
    message: str
    category: Optional[str] = None
    is_anonymous: bool = False

    # community | private | mixed
    visibility: str = "community"

    # selected pastors/members
    recipients: List[PrayerRecipientCreate] = []


class PrayerUpdateStatus(BaseModel):
    status: str
    answer_testimony: str | None = None


class PrayerReactionCreate(BaseModel):
    reaction_type: str


class PrayerCommentCreate(BaseModel):
    comment: str
    parent_id: Optional[int] = None


class PrayerReportCreate(BaseModel):
    reason: str
    details: Optional[str] = None


class PrayerOut(BaseModel):
    id: int
    message: str
    user_name: str
    category: Optional[str]
    visibility: Optional[str]
    status: str
    is_anonymous: bool
    prayer_count: int
    support_count: int
    comment_count: int
    share_count: int
    created_at: datetime

    class Config:
        from_attributes = True