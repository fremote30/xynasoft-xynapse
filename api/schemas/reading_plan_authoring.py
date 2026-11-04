"""
Request contracts for XynaFaith V2 Church Space reading-plan authoring.
"""

from pydantic import BaseModel, Field


class ReadingPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ReadingPlanUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    status: str | None = None


class ReadingPlanDayCreate(BaseModel):
    day_number: int = Field(ge=1)
    title: str | None = Field(
        default=None,
        max_length=200,
    )
    scripture: str = Field(
        min_length=1,
        max_length=500,
    )
    reflection: str | None = None
    prompt: str | None = None


class ReadingPlanDayUpdate(BaseModel):
    day_number: int | None = Field(
        default=None,
        ge=1,
    )
    title: str | None = Field(
        default=None,
        max_length=200,
    )
    scripture: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
    reflection: str | None = None
    prompt: str | None = None
