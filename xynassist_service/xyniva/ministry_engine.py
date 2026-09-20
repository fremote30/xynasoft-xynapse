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
    BiblicalResearchInput,
    BiblicalResearchOutput,
    MinistrySkillName,
    SermonGenerateInput,
    SermonOutput,
    SermonRefineInput,
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


def execute_ministry_skill(
    *,
    skill: MinistrySkillName,
    payload: dict[str, Any],
    provider_name: str,
) -> SermonOutput | BiblicalResearchOutput:
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

    raise ValueError(
        f"Unsupported ministry skill: {skill}"
    )
