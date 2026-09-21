from __future__ import annotations

from dataclasses import dataclass, field
import json

import pytest

from xynassist_service.ai.contracts import (
    ModelRequest,
    ModelResponse,
)
from xynassist_service.ai.registry import (
    clear_model_providers,
    register_model_provider,
)
from xynassist_service.xyniva.ministry_engine import (
    MinistrySkillOutputError,
    execute_biblical_research,
    execute_ministry_skill,
    execute_sermon_generate,
    execute_sermon_refine,
)
from xynassist_service.xyniva.ministry_skills import (
    BibleStudyGenerateInput,
    BibleStudyOutput,
    BiblicalResearchInput,
    ContentTransformInput,
    ContentTransformOutput,
    DevotionalGenerateInput,
    DevotionalOutput,
    SermonGenerateInput,
    SermonOutput,
    SermonRefineInput,
    SermonSeriesGenerateInput,
    SermonSeriesOutput,
)


def sermon_json(
    *,
    scripture: str = "Provider scripture",
) -> str:
    return json.dumps(
        {
            "title": "Trust in the Lord",
            "scripture": scripture,
            "introduction": "Trust begins with surrender.",
            "main_points": [
                {
                    "title": "Trust God",
                    "content": "Depend on God's wisdom.",
                }
            ],
            "application": "Practice dependence on God.",
            "conclusion": "Trust Him in every path.",
        }
    )


def research_json(
    *,
    scripture: str = "Provider scripture",
) -> str:
    return json.dumps(
        {
            "title": "Romans 8:1 Research",
            "scripture": scripture,
            "summary": "Paul describes freedom from condemnation.",
            "observations": [
                {
                    "heading": "Observation",
                    "content": "The statement begins with therefore.",
                }
            ],
            "interpretation": [
                {
                    "heading": "Interpretation",
                    "content": "It connects to the preceding argument.",
                }
            ],
            "theological_perspectives": [
                {
                    "heading": "Perspectives",
                    "content": (
                        "Traditions may emphasize different "
                        "aspects of the passage."
                    ),
                }
            ],
            "ministry_application": [
                {
                    "heading": "Application",
                    "content": "Teach assurance carefully.",
                }
            ],
            "cautions": [
                "Do not present interpretation as quotation."
            ],
        }
    )



def content_transform_json() -> str:
    return json.dumps(
        {
            "source_title": "Grace",
            "pieces": [
                {
                    "format": "social_post",
                    "title": "Grace",
                    "content": "A short social post about grace.",
                },
                {
                    "format": "whatsapp_summary",
                    "title": "Grace Summary",
                    "content": "A WhatsApp summary about grace.",
                },
            ],
        }
    )


def sermon_series_json(
    *,
    count: int = 3,
) -> str:
    return json.dumps(
        {
            "title": "Living by Grace",
            "description": "A series about God's grace.",
            "sermons": [
                {
                    "sequence": index,
                    "title": f"Grace Part {index}",
                    "scripture": f"Reference {index}",
                    "theme": f"Grace theme {index}",
                    "summary": f"Grace summary {index}",
                    "key_points": [
                        f"Grace point {index}",
                    ],
                }
                for index in range(1, count + 1)
            ],
        }
    )


def bible_study_json(
    *,
    scripture: str = "Provider scripture",
) -> str:
    return json.dumps(
        {
            "title": "Saved by Grace",
            "scripture": scripture,
            "objective": "Understand salvation by grace.",
            "opening": "Introduce the passage.",
            "sections": [
                {
                    "heading": "Observe",
                    "content": "Observe the argument in the text.",
                }
            ],
            "discussion_questions": [
                "What does the passage teach about grace?"
            ],
            "application": "Respond to grace with faithful living.",
            "closing_prayer_prompt": (
                "Invite participants to thank God for grace."
            ),
        }
    )


def devotional_json(
    *,
    days: int = 3,
) -> str:
    return json.dumps(
        {
            "title": "Hope Each Day",
            "entries": [
                {
                    "day": day,
                    "title": f"Hope Day {day}",
                    "scripture": f"Reference {day}",
                    "reflection": f"Reflection {day}",
                    "application": f"Application {day}",
                    "prayer": f"Suggested prayer {day}",
                }
                for day in range(1, days + 1)
            ],
        }
    )


@dataclass
class FakeProvider:
    response_content: str
    requests: list[ModelRequest] = field(
        default_factory=list
    )

    @property
    def name(self) -> str:
        return "fake"

    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self.requests.append(request)

        return ModelResponse(
            content=self.response_content,
            provider=self.name,
            model="fake-ministry-v1",
            input_tokens=20,
            output_tokens=30,
        )


@pytest.fixture(autouse=True)
def reset_provider_registry():
    clear_model_providers()

    yield

    clear_model_providers()


def test_sermon_generate_uses_provider_independent_contract():
    provider = FakeProvider(
        sermon_json()
    )
    register_model_provider(provider)

    result = execute_sermon_generate(
        payload=SermonGenerateInput(
            input="Trusting God",
            scripture="Proverbs 3:5-6",
            denomination="pentecostal",
            audience="young adults",
        ),
        provider_name="fake",
    )

    assert result.title == "Trust in the Lord"

    # Caller-selected scripture remains authoritative.
    assert result.scripture == "Proverbs 3:5-6"

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert request.max_output_tokens == 4000
    assert request.messages[0].role == "system"
    assert "You are Xyniva" in request.messages[0].content

    assert request.messages[1].role == "system"
    assert "sermon.generate" in request.messages[1].content

    assert request.messages[-1].role == "user"

    supplied = json.loads(
        request.messages[-1].content
    )

    assert supplied["input"] == "Trusting God"
    assert supplied["scripture"] == "Proverbs 3:5-6"
    assert supplied["denomination"] == "pentecostal"


def test_sermon_refine_returns_complete_sermon():
    provider = FakeProvider(
        sermon_json(
            scripture="Psalm 23",
        )
    )
    register_model_provider(provider)

    existing = SermonOutput.model_validate(
        json.loads(
            sermon_json(
                scripture="Psalm 23",
            )
        )
    )

    result = execute_sermon_refine(
        payload=SermonRefineInput(
            sermon=existing,
            instruction=(
                "Make the application more pastoral."
            ),
        ),
        provider_name="fake",
    )

    assert isinstance(result, SermonOutput)
    assert result.scripture == "Psalm 23"

    supplied = json.loads(
        provider.requests[0].messages[-1].content
    )

    assert (
        supplied["instruction"]
        == "Make the application more pastoral."
    )
    assert supplied["sermon"]["title"] == "Trust in the Lord"


def test_biblical_research_preserves_requested_scripture():
    provider = FakeProvider(
        research_json()
    )
    register_model_provider(provider)

    result = execute_biblical_research(
        payload=BiblicalResearchInput(
            scripture="Romans 8:1",
            question=(
                "What does condemnation mean here?"
            ),
            denomination="methodist",
        ),
        provider_name="fake",
    )

    assert result.scripture == "Romans 8:1"
    assert result.observations
    assert result.interpretation
    assert result.theological_perspectives
    assert result.ministry_application

    request = provider.requests[0]

    assert request.max_output_tokens == 3500
    assert (
        "Separate textual observations from interpretation"
        in request.messages[1].content
    )


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "```json\n{}\n```",
        "prefix " + sermon_json(),
        "[]",
        "{}",
    ],
)
def test_ministry_output_parser_fails_closed(raw):
    provider = FakeProvider(raw)
    register_model_provider(provider)

    with pytest.raises(
        MinistrySkillOutputError,
    ):
        execute_sermon_generate(
            payload=SermonGenerateInput(
                input="Grace",
            ),
            provider_name="fake",
        )


def test_dispatches_sermon_generate():
    provider = FakeProvider(
        sermon_json()
    )
    register_model_provider(provider)

    result = execute_ministry_skill(
        skill="sermon.generate",
        payload={
            "input": "Grace",
        },
        provider_name="fake",
    )

    assert isinstance(result, SermonOutput)


def test_dispatches_biblical_research():
    provider = FakeProvider(
        research_json()
    )
    register_model_provider(provider)

    result = execute_ministry_skill(
        skill="biblical.research",
        payload={
            "topic": "Christian hope",
        },
        provider_name="fake",
    )

    assert result.title == "Romans 8:1 Research"


def test_dispatch_rejects_unknown_skill():
    provider = FakeProvider(
        sermon_json()
    )
    register_model_provider(provider)

    with pytest.raises(
        ValueError,
        match="Unsupported ministry skill",
    ):
        execute_ministry_skill(
            skill="unknown",  # type: ignore[arg-type]
            payload={
                "input": "Grace",
            },
            provider_name="fake",
        )

    assert provider.requests == []



def test_dispatches_content_transform_with_exact_formats():
    provider = FakeProvider(
        content_transform_json()
    )
    register_model_provider(provider)

    result = execute_ministry_skill(
        skill="content.transform",
        payload={
            "source_title": "Grace",
            "source_content": "A sermon about grace.",
            "formats": [
                "social_post",
                "whatsapp_summary",
            ],
        },
        provider_name="fake",
    )

    assert isinstance(result, ContentTransformOutput)

    assert [
        piece.format
        for piece in result.pieces
    ] == [
        "social_post",
        "whatsapp_summary",
    ]

    request = provider.requests[0]

    assert request.max_output_tokens == 4000
    assert (
        "content.transform"
        in request.messages[1].content
    )


def test_content_transform_rejects_missing_requested_format():
    provider = FakeProvider(
        json.dumps(
            {
                "source_title": "Grace",
                "pieces": [
                    {
                        "format": "social_post",
                        "title": "Grace",
                        "content": "Social content.",
                    }
                ],
            }
        )
    )
    register_model_provider(provider)

    with pytest.raises(
        MinistrySkillOutputError,
        match="unexpected number",
    ):
        execute_ministry_skill(
            skill="content.transform",
            payload={
                "source_content": "A sermon about grace.",
                "formats": [
                    "social_post",
                    "whatsapp_summary",
                ],
            },
            provider_name="fake",
        )


def test_dispatches_sermon_series_with_exact_sequence():
    provider = FakeProvider(
        sermon_series_json(
            count=3,
        )
    )
    register_model_provider(provider)

    result = execute_ministry_skill(
        skill="sermon.series.generate",
        payload={
            "topic": "Grace",
            "number_of_sermons": 3,
        },
        provider_name="fake",
    )

    assert isinstance(result, SermonSeriesOutput)
    assert len(result.sermons) == 3

    assert [
        sermon.sequence
        for sermon in result.sermons
    ] == [1, 2, 3]

    assert (
        provider.requests[0].max_output_tokens
        == 5000
    )


def test_sermon_series_rejects_wrong_count():
    provider = FakeProvider(
        sermon_series_json(
            count=2,
        )
    )
    register_model_provider(provider)

    with pytest.raises(
        MinistrySkillOutputError,
        match="unexpected sermon count",
    ):
        execute_ministry_skill(
            skill="sermon.series.generate",
            payload={
                "topic": "Grace",
                "number_of_sermons": 3,
            },
            provider_name="fake",
        )


def test_bible_study_preserves_requested_scripture():
    provider = FakeProvider(
        bible_study_json()
    )
    register_model_provider(provider)

    result = execute_ministry_skill(
        skill="bible_study.generate",
        payload={
            "scripture": "Ephesians 2:8-10",
            "audience": "young adults",
        },
        provider_name="fake",
    )

    assert isinstance(result, BibleStudyOutput)

    assert (
        result.scripture
        == "Ephesians 2:8-10"
    )

    supplied = json.loads(
        provider.requests[0]
        .messages[-1]
        .content
    )

    assert (
        supplied["scripture"]
        == "Ephesians 2:8-10"
    )


def test_dispatches_devotional_with_exact_day_sequence():
    provider = FakeProvider(
        devotional_json(
            days=3,
        )
    )
    register_model_provider(provider)

    result = execute_ministry_skill(
        skill="devotional.generate",
        payload={
            "topic": "Hope",
            "days": 3,
        },
        provider_name="fake",
    )

    assert isinstance(result, DevotionalOutput)

    assert [
        entry.day
        for entry in result.entries
    ] == [1, 2, 3]

    assert (
        provider.requests[0].max_output_tokens
        == 5000
    )


def test_devotional_rejects_wrong_day_sequence():
    raw = json.loads(
        devotional_json(
            days=3,
        )
    )

    raw["entries"][1]["day"] = 3
    raw["entries"][2]["day"] = 2

    provider = FakeProvider(
        json.dumps(raw)
    )
    register_model_provider(provider)

    with pytest.raises(
        MinistrySkillOutputError,
        match="day sequence",
    ):
        execute_ministry_skill(
            skill="devotional.generate",
            payload={
                "topic": "Hope",
                "days": 3,
            },
            provider_name="fake",
        )
