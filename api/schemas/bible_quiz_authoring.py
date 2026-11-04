"""
XynaFaith V2 Bible Quiz authoring request schemas.

Church authorization and entitlements are enforced by API dependencies.
These schemas validate author-supplied content only.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Difficulty = Literal["beginner", "intermediate", "advanced"]
AnswerOption = Literal["A", "B", "C", "D"]


class BibleQuizCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    scripture: str | None = Field(default=None, max_length=500)
    difficulty: Difficulty = "beginner"

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Quiz title cannot be blank")
        return value


class BibleQuizUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    scripture: str | None = Field(default=None, max_length=500)
    difficulty: Difficulty | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Quiz title cannot be null")
        value = value.strip()
        if not value:
            raise ValueError("Quiz title cannot be blank")
        return value


class BibleQuizQuestionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: int = Field(ge=1)
    question_text: str = Field(min_length=1)
    option_a: str = Field(min_length=1)
    option_b: str = Field(min_length=1)
    option_c: str = Field(min_length=1)
    option_d: str = Field(min_length=1)
    correct_option: AnswerOption
    explanation: str | None = None

    @field_validator(
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question and options cannot be blank")
        return value


class BibleQuizQuestionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: int | None = Field(default=None, ge=1)
    question_text: str | None = Field(default=None, min_length=1)
    option_a: str | None = Field(default=None, min_length=1)
    option_b: str | None = Field(default=None, min_length=1)
    option_c: str | None = Field(default=None, min_length=1)
    option_d: str | None = Field(default=None, min_length=1)
    correct_option: AnswerOption | None = None
    explanation: str | None = None

    @field_validator(
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
    )
    @classmethod
    def validate_required_text(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Question and options cannot be null")
        value = value.strip()
        if not value:
            raise ValueError("Question and options cannot be blank")
        return value
