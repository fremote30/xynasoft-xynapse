"""
XynaFaith V2 Bible Quiz submission schemas.

The client supplies answers only. Scores and correctness are
computed exclusively by the server.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BibleQuizSubmittedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(gt=0)
    selected_option: Literal["A", "B", "C", "D"]


class BibleQuizSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[BibleQuizSubmittedAnswer] = Field(min_length=1)
