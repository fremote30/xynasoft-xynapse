"""
XynaFaith V2 ministry AI orchestration.

This is the product boundary connecting:
- authenticated XynaFaith identity
- commercial entitlement/quota reservation
- trusted standalone XynAssist execution
- durable quota consumption/release

The existing V1 sermon endpoint is intentionally not changed here.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session
from api.models.ai_usage_reservation import AIUsageReservation
from api.services.ministry_skill_metering import ministry_skill_access
from api.services.ai_usage_metering import (
    RESERVATION_RESERVED,
    RESERVATION_CONSUMED,
    RESERVATION_RELEASED,
)


from api.models.user import User
from api.services.ministry_skill_metering import (
    reserve_ministry_skill,
    consume_ministry_skill,
    release_ministry_skill,
)
from api.services.xynassist_client import (
    XynAssistClient,
    XynAssistConfigurationError,
    XynAssistResponseError,
    XynAssistUnavailableError,
)


class MinistryExecutionError(RuntimeError):
    """Base product-level ministry execution failure."""


class MinistryExecutionUncertainError(
    MinistryExecutionError
):
    """
    XynAssist may have received or executed the request.

    The durable usage reservation is intentionally retained so a
    potentially completed remote AI call cannot be re-spent locally.
    """


async def reconcile_ministry_for_user(
    db: Session,
    *,
    user: User,
    request_id: str,
    client: XynAssistClient | None = None,
) -> dict[str, Any]:
    """
    Reconcile one existing, user-owned ministry reservation.

    This operation never reserves new quota or starts AI generation.
    """
    from uuid import UUID

    normalized_id = str(UUID(request_id))

    reservation = (
        db.query(AIUsageReservation)
        .filter(
            AIUsageReservation.request_id == normalized_id,
            AIUsageReservation.user_id == user.id,
        )
        .one_or_none()
    )

    if reservation is None:
        raise MinistryExecutionError(
            "Ministry execution not found"
        )

    supported = {
        "sermon.generate",
        "content.transform",
    }

    matching_skills = [
        skill
        for skill in supported
        if ministry_skill_access(skill) == (
            reservation.entitlement_key,
            reservation.metric,
        )
    ]

    if len(matching_skills) != 1:
        raise MinistryExecutionError(
            "Reservation is not a supported ministry execution"
        )

    expected_skill = matching_skills[0]

    if reservation.status == RESERVATION_RELEASED:
        raise MinistryExecutionError(
            "Ministry reservation has been released"
        )

    if reservation.status not in {
        RESERVATION_RESERVED,
        RESERVATION_CONSUMED,
    }:
        raise MinistryExecutionError(
            "Invalid ministry reservation state"
        )

    xynassist = client or XynAssistClient()

    remote = await xynassist.get_ministry_execution_status(
        external_user_id=str(user.id),
        request_id=normalized_id,
    )

    if not isinstance(remote, dict):
        raise MinistryExecutionError(
            "Invalid remote ministry execution response"
        )

    if (
        remote.get("request_id") != normalized_id
        or remote.get("skill") != expected_skill
    ):
        raise MinistryExecutionError(
            "Remote ministry execution does not match reservation"
        )

    remote_status = remote.get("status")
    if remote_status not in {
        "in_progress",
        "completed",
        "failed",
        "uncertain",
    }:
        raise MinistryExecutionError(
            "Invalid remote ministry execution status"
        )

    remote_result = remote.get("result")
    if remote_status == "completed":
        if not isinstance(remote_result, dict) or not remote_result:
            raise MinistryExecutionError(
                "Completed ministry execution has no valid result"
            )
    elif remote_result is not None:
        raise MinistryExecutionError(
            "Incomplete ministry execution returned a result"
        )

    if remote_status == "completed":
        if reservation.status == RESERVATION_RESERVED:
            consume_ministry_skill(
                db,
                request_id=normalized_id,
            )

        return {
            "request_id": normalized_id,
            "skill": expected_skill,
            "status": "completed",
            "result": remote_result,
        }

    return {
        "request_id": normalized_id,
        "skill": expected_skill,
        "status": remote_status,
        "result": None,
    }


async def execute_ministry_for_user(
    db: Session,
    *,
    user: User,
    request_id: str,
    skill: str,
    payload: dict[str, Any],
    church_id: Optional[int] = None,
    client: XynAssistClient | None = None,
) -> dict[str, Any]:
    """
    Execute one metered XynaFaith ministry intelligence skill.

    Transaction semantics:

    1. Reserve and commit quota before external AI work.
    2. Execute through trusted XynAssist identity headers.
    3. Consume and commit after successful structured output.
    4. Release on definite pre-success failure.
    5. Retain reservation when remote execution state is uncertain.
    6. Never release after successful AI output merely because local
       consumption fails.
    """

    # Validate skill + entitlement and durably reserve quota first.
    reserve_ministry_skill(
        db,
        user=user,
        request_id=request_id,
        skill=skill,
        church_id=church_id,
    )

    xynassist = client or XynAssistClient()

    try:
        result = await xynassist.execute_ministry_skill(
            external_user_id=str(user.id),
            request_id=request_id,
            skill=skill,
            payload=payload,
        )

    except XynAssistUnavailableError as exc:
        # A transport failure does not prove the remote request was never
        # received. Keep the reservation rather than permitting re-spend.
        raise MinistryExecutionUncertainError(
            "XynAssist ministry execution state is uncertain"
        ) from exc

    except XynAssistConfigurationError:
        # Local configuration prevented the trusted request from starting.
        release_ministry_skill(
            db,
            request_id=request_id,
        )
        raise

    except XynAssistResponseError as exc:
        # Remote HTTP errors, conflicts, and malformed responses do not
        # prove that provider execution never started. Retain quota.
        raise MinistryExecutionUncertainError(
            "XynAssist ministry execution state is uncertain"
        ) from exc

    # AI work succeeded. From this point onward the reservation must never
    # be released, even if local consumption persistence fails.
    consume_ministry_skill(
        db,
        request_id=request_id,
    )

    return result
