"""Bible Quiz generation input contract regression tests."""

import pytest
from pydantic import ValidationError

from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
    generation_input_fingerprint,
)


BASE_INPUT = {
    "church_id": 1,
    "creator_user_id": 7,
    "topic": "Trusting God",
    "scripture": "Proverbs 3:5-6",
    "difficulty": "beginner",
    "question_count": 5,
}


@pytest.mark.parametrize(
    "difficulty",
    ["beginner", "intermediate", "advanced"],
)
def test_supported_difficulty(difficulty):
    inputs = BibleQuizGenerationInputs(
        **{**BASE_INPUT, "difficulty": difficulty}
    )
    assert inputs.difficulty == difficulty


@pytest.mark.parametrize(
    "difficulty",
    ["expert", "easy", "", None],
)
def test_unsupported_difficulty_rejected(difficulty):
    with pytest.raises(ValidationError):
        BibleQuizGenerationInputs(
            **{**BASE_INPUT, "difficulty": difficulty}
        )


@pytest.mark.parametrize("count", [0, 51])
def test_invalid_question_count_rejected(count):
    with pytest.raises(ValidationError):
        BibleQuizGenerationInputs(
            **{**BASE_INPUT, "question_count": count}
        )


def test_fingerprint_is_stable():
    first = BibleQuizGenerationInputs(**BASE_INPUT)
    second = BibleQuizGenerationInputs(**BASE_INPUT)

    assert generation_input_fingerprint(first) == (
        generation_input_fingerprint(second)
    )


def test_fingerprint_changes_with_input():
    first = BibleQuizGenerationInputs(**BASE_INPUT)
    second = BibleQuizGenerationInputs(
        **{**BASE_INPUT, "topic": "Faith"}
    )

    assert generation_input_fingerprint(first) != (
        generation_input_fingerprint(second)
    )
