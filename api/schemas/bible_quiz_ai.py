"""Public contracts for AI Bible Quiz generation and recovery."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


BibleQuizDifficulty = Literal[
    "beginner",
    "intermediate",
    "advanced",
]

BibleQuizGenerationStatus = Literal[
    "pending",
    "running",
    "uncertain",
    "completed",
    "failed",
]


class BibleQuizAIGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    topic: str = Field(min_length=1, max_length=200)
    scripture: str = Field(min_length=1, max_length=500)
    difficulty: BibleQuizDifficulty
    question_count: int = Field(ge=1, le=50)


class BibleQuizAIGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    status: BibleQuizGenerationStatus
    quiz_id: int | None = None
