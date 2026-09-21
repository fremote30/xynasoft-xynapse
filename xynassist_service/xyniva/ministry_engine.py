"""
Provider-independent Xyniva ministry skill execution.

Ministry skills generate structured content. They do not authorize or
perform XynaFaith product mutations.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from xynassist_service.ai.contracts import (
    ModelMessage,
    ModelRequest,
)
from xynassist_service.ai.registry import (
    get_model_provider,
)
from xynassist_service.xyniva.ministry_skills import (
    BibleStudyGenerateInput,
    BibleStudyOutput,
    BiblicalResearchInput,
    BiblicalResearchOutput,
    ContentTransformInput,
    ContentTransformOutput,
    DevotionalGenerateInput,
    DevotionalOutput,
    MinistrySkillName,
    SermonGenerateInput,
    SermonOutput,
    SermonRefineInput,
    SermonSeriesGenerateInput,
    SermonSeriesOutput,
)
from xynassist_service.xyniva.policy import (
    XYNIVA_SYSTEM_POLICY,
)


class MinistrySkillOutputError(ValueError):
    """Raised when a ministry skill returns invalid structured output."""


SERMON_GENERATE_POLICY = """
You are executing Xyniva's sermon.generate ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "title": "string",
  "scripture": "string",
  "introduction": "string",
  "main_points": [
    {
      "title": "string",
      "content": "string"
    }
  ],
  "application": "string",
  "conclusion": "string"
}

Requirements:
- Produce a coherent, biblically grounded, preachable sermon.
- Respect the supplied topic, scripture, denomination, audience,
  ministry context, tone, and requested duration.
- If scripture was supplied, preserve that scripture reference.
- Distinguish biblical text from interpretation and application.
- Never invent Bible quotations, citations, historical sources, or facts.
- Do not claim divine revelation or prophetic certainty.
- Return raw JSON only. Never use Markdown code fences.
""".strip()


SERMON_REFINE_POLICY = """
You are executing Xyniva's sermon.refine ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "title": "string",
  "scripture": "string",
  "introduction": "string",
  "main_points": [
    {
      "title": "string",
      "content": "string"
    }
  ],
  "application": "string",
  "conclusion": "string"
}

Requirements:
- Refine the supplied sermon according to the explicit instruction.
- Preserve sound material that the instruction does not require changing.
- Respect supplied denomination, audience, ministry context, and tone.
- Distinguish biblical text from interpretation and application.
- Never invent Bible quotations, citations, historical sources, or facts.
- Do not claim divine revelation or prophetic certainty.
- Return the complete refined sermon, not a patch or commentary.
- Return raw JSON only. Never use Markdown code fences.
""".strip()


BIBLICAL_RESEARCH_POLICY = """
You are executing Xyniva's biblical.research ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "title": "string",
  "scripture": "string",
  "summary": "string",
  "observations": [
    {"heading": "string", "content": "string"}
  ],
  "interpretation": [
    {"heading": "string", "content": "string"}
  ],
  "theological_perspectives": [
    {"heading": "string", "content": "string"}
  ],
  "ministry_application": [
    {"heading": "string", "content": "string"}
  ],
  "cautions": ["string"]
}

Requirements:
- Separate textual observations from interpretation.
- Separate interpretation from ministry application.
- When Christian traditions reasonably differ, describe the relevant
  perspectives without pretending one is universally settled.
- Use supplied denomination context when useful without disparaging
  other traditions.
- Never invent Bible quotations, citations, historical sources, or facts.
- Do not fabricate Greek/Hebrew definitions, manuscript evidence,
  scholarly claims, or source references.
- If reliable support for a requested factual claim is unavailable,
  state the limitation in cautions rather than inventing support.
- Do not claim divine revelation or prophetic certainty.
- Return raw JSON only. Never use Markdown code fences.
""".strip()



CONTENT_TRANSFORM_POLICY = """
You are executing Xyniva's content.transform ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "source_title": "string",
  "pieces": [
    {
      "format": "requested format",
      "title": "string",
      "content": "string"
    }
  ]
}

Requirements:
- Transform the supplied source material without changing its core meaning.
- Return exactly one piece for every requested format.
- Do not introduce unsupported factual, biblical, or historical claims.
- Preserve supplied scripture references accurately.
- Respect the supplied audience, denomination, context, and tone.
- A devotional output may apply the source pastorally, but must
  distinguish scripture from interpretation and application.
- Never invent Bible quotations, citations, historical sources, or facts.
- Do not claim divine revelation or prophetic certainty.
- Return raw JSON only. Never use Markdown code fences.
""".strip()


SERMON_SERIES_POLICY = """
You are executing Xyniva's sermon.series.generate ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "title": "string",
  "description": "string",
  "sermons": [
    {
      "sequence": 1,
      "title": "string",
      "scripture": "string",
      "theme": "string",
      "summary": "string",
      "key_points": ["string"]
    }
  ]
}

Requirements:
- Build one coherent sermon series around the supplied subject.
- Return exactly the requested number of sermons.
- Sequence sermons from 1 through the requested count.
- Give each sermon a distinct purpose while maintaining series continuity.
- Respect denomination, audience, ministry context, and tone.
- Distinguish biblical text from interpretation and application.
- Never invent Bible quotations, citations, historical sources, or facts.
- Do not claim divine revelation or prophetic certainty.
- Return raw JSON only. Never use Markdown code fences.
""".strip()


BIBLE_STUDY_POLICY = """
You are executing Xyniva's bible_study.generate ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "title": "string",
  "scripture": "string",
  "objective": "string",
  "opening": "string",
  "sections": [
    {
      "heading": "string",
      "content": "string"
    }
  ],
  "discussion_questions": ["string"],
  "application": "string",
  "closing_prayer_prompt": "string"
}

Requirements:
- Create a teachable Bible study appropriate to the requested session.
- Respect supplied scripture, topic, audience, denomination, and context.
- Separate textual observation, interpretation, and application.
- Discussion questions should promote thoughtful engagement with the text.
- When Christian traditions reasonably differ, do not present one
  interpretation as universally settled.
- Never invent Bible quotations, citations, historical sources, or facts.
- Do not fabricate Greek/Hebrew definitions or scholarly claims.
- Do not claim divine revelation or prophetic certainty.
- Return raw JSON only. Never use Markdown code fences.
""".strip()


DEVOTIONAL_POLICY = """
You are executing Xyniva's devotional.generate ministry skill.

Return exactly one raw JSON object and no other text.

Required JSON shape:
{
  "title": "string",
  "entries": [
    {
      "day": 1,
      "title": "string",
      "scripture": "string",
      "reflection": "string",
      "application": "string",
      "prayer": "string"
    }
  ]
}

Requirements:
- Return exactly the requested number of devotional entries.
- Number entries sequentially beginning with day 1.
- Keep each entry useful as a standalone daily devotional while
  maintaining continuity when multiple days are requested.
- Respect supplied topic, scripture, audience, denomination, context,
  and tone.
- Distinguish biblical text from interpretation and application.
- Prayer text must be presented as a suggested prayer, never as divine
  revelation or a guaranteed outcome.
- Never invent Bible quotations, citations, historical sources, or facts.
- Return raw JSON only. Never use Markdown code fences.
""".strip()


def _serialize_input(value: BaseModel) -> str:
    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _parse_output(
    raw_content: str,
    output_model: type[BaseModel],
) -> BaseModel:
    """
    Strictly parse one ministry-skill JSON object.

    Deliberately performs no Markdown stripping, prose extraction,
    malformed-JSON repair, or semantic inference.
    """

    if not isinstance(raw_content, str):
        raise MinistrySkillOutputError(
            "Ministry skill output must be text"
        )

    normalized = raw_content.strip()

    if not normalized:
        raise MinistrySkillOutputError(
            "Ministry skill output is empty"
        )

    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise MinistrySkillOutputError(
            "Ministry skill output is not valid JSON"
        ) from exc

    if not isinstance(decoded, dict):
        raise MinistrySkillOutputError(
            "Ministry skill output must be a JSON object"
        )

    try:
        return output_model.model_validate(decoded)
    except ValidationError as exc:
        raise MinistrySkillOutputError(
            "Ministry skill output failed validation"
        ) from exc


def _execute_skill(
    *,
    policy: str,
    payload: BaseModel,
    output_model: type[BaseModel],
    provider_name: str,
    max_output_tokens: int,
) -> tuple[BaseModel, str, str]:
    provider = get_model_provider(provider_name)

    request = ModelRequest(
        messages=(
            ModelMessage(
                role="system",
                content=XYNIVA_SYSTEM_POLICY,
            ),
            ModelMessage(
                role="system",
                content=policy,
            ),
            ModelMessage(
                role="user",
                content=_serialize_input(payload),
            ),
        ),
        max_output_tokens=max_output_tokens,
    )

    response = provider.generate(request)

    parsed = _parse_output(
        response.content,
        output_model,
    )

    return parsed, response.provider, response.model


def execute_sermon_generate(
    *,
    payload: SermonGenerateInput,
    provider_name: str,
) -> SermonOutput:
    result, _, _ = _execute_skill(
        policy=SERMON_GENERATE_POLICY,
        payload=payload,
        output_model=SermonOutput,
        provider_name=provider_name,
        max_output_tokens=4000,
    )

    assert isinstance(result, SermonOutput)

    # Existing XynaFaith compatibility behavior treats the caller's
    # scripture selection as authoritative.
    if payload.scripture:
        result = result.model_copy(
            update={
                "scripture": payload.scripture,
            }
        )

    return result


def execute_sermon_refine(
    *,
    payload: SermonRefineInput,
    provider_name: str,
) -> SermonOutput:
    result, _, _ = _execute_skill(
        policy=SERMON_REFINE_POLICY,
        payload=payload,
        output_model=SermonOutput,
        provider_name=provider_name,
        max_output_tokens=4000,
    )

    assert isinstance(result, SermonOutput)

    return result


def execute_biblical_research(
    *,
    payload: BiblicalResearchInput,
    provider_name: str,
) -> BiblicalResearchOutput:
    result, _, _ = _execute_skill(
        policy=BIBLICAL_RESEARCH_POLICY,
        payload=payload,
        output_model=BiblicalResearchOutput,
        provider_name=provider_name,
        max_output_tokens=3500,
    )

    assert isinstance(result, BiblicalResearchOutput)

    if payload.scripture:
        result = result.model_copy(
            update={
                "scripture": payload.scripture,
            }
        )

    return result



def execute_content_transform(
    *,
    payload: ContentTransformInput,
    provider_name: str,
) -> ContentTransformOutput:
    result, _, _ = _execute_skill(
        policy=CONTENT_TRANSFORM_POLICY,
        payload=payload,
        output_model=ContentTransformOutput,
        provider_name=provider_name,
        max_output_tokens=4000,
    )

    assert isinstance(result, ContentTransformOutput)

    requested = list(payload.formats)
    returned = [piece.format for piece in result.pieces]

    if len(returned) != len(requested):
        raise MinistrySkillOutputError(
            "Content transform returned an unexpected number of pieces"
        )

    if set(returned) != set(requested):
        raise MinistrySkillOutputError(
            "Content transform returned unexpected formats"
        )

    return result


def execute_sermon_series_generate(
    *,
    payload: SermonSeriesGenerateInput,
    provider_name: str,
) -> SermonSeriesOutput:
    result, _, _ = _execute_skill(
        policy=SERMON_SERIES_POLICY,
        payload=payload,
        output_model=SermonSeriesOutput,
        provider_name=provider_name,
        max_output_tokens=5000,
    )

    assert isinstance(result, SermonSeriesOutput)

    if len(result.sermons) != payload.number_of_sermons:
        raise MinistrySkillOutputError(
            "Sermon series returned an unexpected sermon count"
        )

    expected_sequence = list(
        range(1, payload.number_of_sermons + 1)
    )
    actual_sequence = [
        sermon.sequence
        for sermon in result.sermons
    ]

    if actual_sequence != expected_sequence:
        raise MinistrySkillOutputError(
            "Sermon series sequence is invalid"
        )

    return result


def execute_bible_study_generate(
    *,
    payload: BibleStudyGenerateInput,
    provider_name: str,
) -> BibleStudyOutput:
    result, _, _ = _execute_skill(
        policy=BIBLE_STUDY_POLICY,
        payload=payload,
        output_model=BibleStudyOutput,
        provider_name=provider_name,
        max_output_tokens=4000,
    )

    assert isinstance(result, BibleStudyOutput)

    if payload.scripture:
        result = result.model_copy(
            update={
                "scripture": payload.scripture,
            }
        )

    return result


def execute_devotional_generate(
    *,
    payload: DevotionalGenerateInput,
    provider_name: str,
) -> DevotionalOutput:
    result, _, _ = _execute_skill(
        policy=DEVOTIONAL_POLICY,
        payload=payload,
        output_model=DevotionalOutput,
        provider_name=provider_name,
        max_output_tokens=5000,
    )

    assert isinstance(result, DevotionalOutput)

    if len(result.entries) != payload.days:
        raise MinistrySkillOutputError(
            "Devotional returned an unexpected entry count"
        )

    expected_days = list(
        range(1, payload.days + 1)
    )
    actual_days = [
        entry.day
        for entry in result.entries
    ]

    if actual_days != expected_days:
        raise MinistrySkillOutputError(
            "Devotional day sequence is invalid"
        )

    return result


def execute_ministry_skill(
    *,
    skill: MinistrySkillName,
    payload: dict[str, Any],
    provider_name: str,
) -> (
    SermonOutput
    | BiblicalResearchOutput
    | ContentTransformOutput
    | SermonSeriesOutput
    | BibleStudyOutput
    | DevotionalOutput
):
    """
    Dispatch a supported ministry skill through its typed contract.
    """

    if skill == "sermon.generate":
        validated = SermonGenerateInput.model_validate(
            payload
        )

        return execute_sermon_generate(
            payload=validated,
            provider_name=provider_name,
        )

    if skill == "sermon.refine":
        validated = SermonRefineInput.model_validate(
            payload
        )

        return execute_sermon_refine(
            payload=validated,
            provider_name=provider_name,
        )

    if skill == "biblical.research":
        validated = BiblicalResearchInput.model_validate(
            payload
        )

        return execute_biblical_research(
            payload=validated,
            provider_name=provider_name,
        )

    if skill == "content.transform":
        validated = ContentTransformInput.model_validate(
            payload
        )

        return execute_content_transform(
            payload=validated,
            provider_name=provider_name,
        )

    if skill == "sermon.series.generate":
        validated = SermonSeriesGenerateInput.model_validate(
            payload
        )

        return execute_sermon_series_generate(
            payload=validated,
            provider_name=provider_name,
        )

    if skill == "bible_study.generate":
        validated = BibleStudyGenerateInput.model_validate(
            payload
        )

        return execute_bible_study_generate(
            payload=validated,
            provider_name=provider_name,
        )

    if skill == "devotional.generate":
        validated = DevotionalGenerateInput.model_validate(
            payload
        )

        return execute_devotional_generate(
            payload=validated,
            provider_name=provider_name,
        )

    raise ValueError(
        f"Unsupported ministry skill: {skill}"
    )
