from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PrayerCreate(BaseModel):
    message: str
    category: Optional[str] = None
    is_anonymous: bool = False


class PrayerUpdateStatus(BaseModel):
    status: str


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
    status: str
    is_anonymous: bool
    prayer_count: int
    support_count: int
    comment_count: int
    share_count: int
    created_at: datetime

    class Config:
        from_attributes = True