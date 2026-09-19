"""
Provider-independent structured intelligence output for Xyniva.

This module describes semantic decisions produced by Xyniva. It does
not authorize or execute actions.

Action proposals remain subject to the receiving product's
authentication, authorization, validation, confirmation, idempotency,
and execution boundaries.

Confirmation signals identify only the pending action being confirmed.
They never carry the durable action target, execution request id, or a
trusted-confirmation flag.
"""

from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from xynassist_service.actions.contracts import (
    get_action_definition,
    is_supported_action,
)
from xynassist_service.actions.schemas import (
    ForgetMemoryArguments,
    RememberMemoryArguments,
)


class XynivaStructuredAction(BaseModel):
    """Validated action proposal emitted by Xyniva."""

    name: str
    arguments: dict = Field(default_factory=dict)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        if not is_supported_action(
            value,
            product="xynafaith",
        ):
            raise ValueError(
                "Unsupported Xyniva action"
            )

        return value

    @model_validator(mode="after")
    def validate_arguments(
        self,
    ) -> "XynivaStructuredAction":
        if self.name == "memory.remember":
            validated = (
                RememberMemoryArguments
                .model_validate(self.arguments)
            )
            self.arguments = validated.model_dump()
            return self

        if self.name == "memory.forget":
            validated = (
                ForgetMemoryArguments
                .model_validate(self.arguments)
            )
            self.arguments = validated.model_dump()
            return self

        # Stage 4C initially enables model-driven memory actions only.
        raise ValueError(
            "Action is not enabled for Xyniva "
            "structured intelligence"
        )


class XynivaConfirmationSignal(BaseModel):
    """
    Semantic confirmation of an already-pending action.

    The receiving product must bind this signal to its own durable
    pending state before any trusted confirmation is issued.
    """

    action_name: str

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("action_name")
    @classmethod
    def validate_action_name(
        cls,
        value: str,
    ) -> str:
        definition = get_action_definition(value)

        if (
            definition is None
            or definition.product != "xynafaith"
            or definition.confirmation != "required"
        ):
            raise ValueError(
                "Confirmation requires a supported "
                "confirmable XynaFaith action"
            )

        return value


class XynivaStructuredOutput(BaseModel):
    """
    One semantic Xyniva result.

    Exactly one of these modes is permitted:
    - response: ordinary conversational content
    - action: a typed action proposal
    - confirmation: confirmation of durable pending state
    """

    kind: Literal[
        "response",
        "action",
        "confirmation",
    ]

    content: str | None = None
    action: XynivaStructuredAction | None = None
    confirmation: XynivaConfirmationSignal | None = None
    prompt: str | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @model_validator(mode="after")
    def validate_mode(
        self,
    ) -> "XynivaStructuredOutput":
        if self.kind == "response":
            if (
                not self.content
                or self.action is not None
                or self.confirmation is not None
                or self.prompt is not None
            ):
                raise ValueError(
                    "Invalid response output"
                )

            return self

        if self.kind == "action":
            if (
                self.action is None
                or self.confirmation is not None
            ):
                raise ValueError(
                    "Invalid action output"
                )

            definition = get_action_definition(
                self.action.name
            )

            if definition is None:
                raise ValueError(
                    "Unknown action definition"
                )

            if definition.confirmation == "required":
                if not self.prompt:
                    raise ValueError(
                        "Confirmable action requires "
                        "a confirmation prompt"
                    )
            elif self.prompt is not None:
                raise ValueError(
                    "Non-confirmable action must not "
                    "include a confirmation prompt"
                )

            return self

        if (
            self.confirmation is None
            or self.action is not None
            or self.prompt is not None
        ):
            raise ValueError(
                "Invalid confirmation output"
            )

        return self


class XynivaStructuredOutputError(ValueError):
    """Raised when model output is not valid structured Xyniva output."""


def parse_xyniva_structured_output(
    raw_content: str,
) -> XynivaStructuredOutput:
    """
    Parse one strict JSON Xyniva intelligence result.

    The parser intentionally does not:
    - strip Markdown code fences
    - extract JSON from surrounding prose
    - repair malformed JSON
    - infer missing semantic fields

    Invalid model output fails closed.
    """

    import json

    from pydantic import ValidationError

    if not isinstance(raw_content, str):
        raise XynivaStructuredOutputError(
            "Xyniva structured output must be text"
        )

    normalized = raw_content.strip()

    if not normalized:
        raise XynivaStructuredOutputError(
            "Xyniva structured output is empty"
        )

    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise XynivaStructuredOutputError(
            "Xyniva structured output is not valid JSON"
        ) from exc

    if not isinstance(decoded, dict):
        raise XynivaStructuredOutputError(
            "Xyniva structured output must be a JSON object"
        )

    try:
        return XynivaStructuredOutput.model_validate(
            decoded
        )
    except ValidationError as exc:
        raise XynivaStructuredOutputError(
            "Xyniva structured output failed validation"
        ) from exc
