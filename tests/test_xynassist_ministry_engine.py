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
    BiblicalResearchInput,
    SermonGenerateInput,
    SermonOutput,
    SermonRefineInput,
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
