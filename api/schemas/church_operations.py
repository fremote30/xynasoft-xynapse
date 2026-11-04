"""Schemas for XynaFaith V2 Church Operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    church_membership_id: int = Field(gt=0)
    status: str = "present"
    checked_in_at: datetime | None = None


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    checked_in_at: datetime | None = None


class ServiceAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: int = Field(gt=0)
    church_membership_id: int = Field(gt=0)
    service_role: str = Field(min_length=1, max_length=120)


class ServiceAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
