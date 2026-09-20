from __future__ import annotations

import pytest
from pydantic import ValidationError

from xynassist_service.xyniva.ministry_skills import (
    BiblicalResearchInput,
    BiblicalResearchOutput,
    SermonGenerateInput,
    SermonOutput,
    SermonRefineInput,
    is_ministry_skill,
)


def valid_sermon() -> dict:
    return {
        "title": "Trust in the Lord",
        "scripture": "Proverbs 3:5-6",
        "introduction": "Trust begins with surrender.",
        "main_points": [
            {
                "title": "Trust God",
                "content": "Depend on God's wisdom.",
            }
        ],
        "application": "Practice daily dependence on God.",
        "conclusion": "Trust Him in every path.",
    }


def test_sermon_generate_preserves_xynafaith_defaults():
    request = SermonGenerateInput(
        input="Grace",
    )

    assert request.input == "Grace"
    assert request.scripture == ""
    assert request.denomination == "general"
    assert request.audience == ""
    assert request.context == ""
    assert request.tone == "balanced"
    assert request.duration == "30"


def test_sermon_generate_supports_scripture_only():
    request = SermonGenerateInput(
        scripture="Psalm 23",
    )

    assert request.input == ""
    assert request.scripture == "Psalm 23"


def test_sermon_generate_requires_topic_or_scripture():
    with pytest.raises(
        ValidationError,
        match="topic or scripture",
    ):
        SermonGenerateInput()


def test_sermon_output_is_strict_and_structured():
    sermon = SermonOutput.model_validate(
        valid_sermon()
    )

    assert sermon.title == "Trust in the Lord"
    assert sermon.main_points[0].title == "Trust God"

    with pytest.raises(ValidationError):
        SermonOutput.model_validate(
            {
                **valid_sermon(),
                "unexpected": "not allowed",
            }
        )


def test_sermon_refine_requires_instruction():
    sermon = SermonOutput.model_validate(
        valid_sermon()
    )

    request = SermonRefineInput(
        sermon=sermon,
        instruction="Make the application more pastoral.",
    )

    assert request.instruction.startswith(
        "Make the application"
    )

    with pytest.raises(ValidationError):
        SermonRefineInput(
            sermon=sermon,
            instruction="",
        )


def test_biblical_research_accepts_scripture():
    request = BiblicalResearchInput(
        scripture="Romans 8:1",
        question="What does condemnation mean here?",
    )

    assert request.scripture == "Romans 8:1"


def test_biblical_research_accepts_topic():
    request = BiblicalResearchInput(
        topic="Christian hope",
    )

    assert request.topic == "Christian hope"


def test_biblical_research_requires_subject():
    with pytest.raises(
        ValidationError,
        match="scripture passage or research topic",
    ):
        BiblicalResearchInput(
            question="Explain this",
        )


def test_research_output_separates_interpretation():
    result = BiblicalResearchOutput.model_validate(
        {
            "title": "Romans 8:1 Research",
            "scripture": "Romans 8:1",
            "summary": "Paul describes freedom from condemnation.",
            "observations": [
                {
                    "heading": "Text",
                    "content": "The verse begins with therefore.",
                }
            ],
            "interpretation": [
                {
                    "heading": "Meaning",
                    "content": (
                        "The statement connects to Paul's "
                        "preceding argument."
                    ),
                }
            ],
            "theological_perspectives": [
                {
                    "heading": "Traditions",
                    "content": (
                        "Christian traditions may emphasize "
                        "different aspects of this passage."
                    ),
                }
            ],
            "ministry_application": [
                {
                    "heading": "Pastoral use",
                    "content": (
                        "The passage can support teaching "
                        "about assurance in Christ."
                    ),
                }
            ],
            "cautions": [
                "Do not present interpretation as a direct quotation."
            ],
        }
    )

    assert result.observations
    assert result.interpretation
    assert result.theological_perspectives
    assert result.ministry_application


def test_research_output_rejects_blank_cautions():
    with pytest.raises(ValidationError):
        BiblicalResearchOutput.model_validate(
            {
                "title": "Research",
                "summary": "Summary",
                "cautions": [""],
            }
        )


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("sermon.generate", True),
        ("sermon.refine", True),
        ("biblical.research", True),
        ("conversation.respond", False),
        ("sermon.save", False),
        ("memory.remember", False),
    ],
)
def test_ministry_skill_registry(
    skill,
    expected,
):
    assert is_ministry_skill(skill) is expected
