"""
Typed argument contracts for XynAssist action proposals.

These schemas validate proposal structure only. They do not
authorize or execute mutations.
"""

from __future__ import annotations

from datetime import datetime

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)


MemoryType = Literal[
    "preference",
    "ministry_context",
    "user_fact",
]


class _MemoryActionBase(BaseModel):
    memory_type: MemoryType
    key: str

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("key")
    @classmethod
    def validate_key(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Memory key is required"
            )

        return value


class RememberMemoryArguments(
    _MemoryActionBase,
):
    value: str

    @field_validator("value")
    @classmethod
    def validate_value(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Memory value is required"
            )

        return value


class ForgetMemoryArguments(
    _MemoryActionBase,
):
    pass

class SaveAnnouncementDraftArguments(BaseModel):
    """
    Untrusted model proposal for one announcement draft.

    Church identity, authenticated user identity, lifecycle status,
    authorization, entitlement, and execution authority are deliberately
    excluded from model-controlled arguments.
    """

    title: str = Field(
        min_length=1,
        max_length=200,
    )
    body: str = Field(
        min_length=1,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

class SaveEventDraftArguments(BaseModel):
    """
    Untrusted model proposal for one Church Space event draft.

    Church identity, authenticated user identity, lifecycle status,
    authorization, entitlement, and execution authority are deliberately
    excluded from model-controlled arguments.
    """

    title: str = Field(
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(
        default=None,
        max_length=255,
    )
    event_url: HttpUrl | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

class CreateServiceAssignmentArguments(BaseModel):
    """
    Proposed volunteer/service assignment.

    Church identity, authenticated actor identity, authorization,
    entitlement, confirmation, and execution authority remain
    controlled by XynaFaith.
    """

    event_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    church_membership_id: int = Field(gt=0)
    service_role: str = Field(
        min_length=1,
        max_length=120,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )



class ReassignServiceAssignmentArguments(BaseModel):
    """
    Proposed volunteer/service assignment reassignment.

    The existing assignment remains historical. XynaFaith controls
    church identity, authorization, entitlement, confirmation, and
    execution authority.
    """

    event_id: int = Field(gt=0)
    assignment_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    church_membership_id: int = Field(gt=0)
    service_role: str = Field(
        min_length=1,
        max_length=120,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )



class UpdateServiceAssignmentStatusArguments(BaseModel):
    """
    Proposed service-assignment lifecycle transition.

    Church identity, authenticated actor identity, authorization,
    entitlement, confirmation, and execution authority remain
    controlled by XynaFaith.
    """

    event_id: int = Field(gt=0)
    assignment_id: int = Field(gt=0)
    status: Literal[
        "confirmed",
        "declined",
        "completed",
        "cancelled",
    ]

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
