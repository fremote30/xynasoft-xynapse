"""Canonical identity for AI Bible Quiz generation requests."""

import hashlib
import json

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BibleQuizGenerationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    church_id: int = Field(gt=0)
    creator_user_id: int = Field(gt=0)
    topic: str = Field(min_length=1, max_length=200)
    scripture: str = Field(min_length=1, max_length=500)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    question_count: int = Field(ge=1, le=50)


def generation_input_fingerprint(
    inputs: BibleQuizGenerationInputs,
) -> str:
    """Produce a stable SHA-256 digest for one generation request."""

    canonical = json.dumps(
        inputs.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
