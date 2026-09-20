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
            skill=skill,
            payload=payload,
        )

    except XynAssistUnavailableError as exc:
        # A transport failure does not prove the remote request was never
        # received. Keep the reservation rather than permitting re-spend.
        raise MinistryExecutionUncertainError(
            "XynAssist ministry execution state is uncertain"
        ) from exc

    except (
        XynAssistConfigurationError,
        XynAssistResponseError,
    ):
        # Configuration failures and explicit/invalid remote responses
        # produced no acceptable ministry result.
        release_ministry_skill(
            db,
            request_id=request_id,
        )
        raise

    # AI work succeeded. From this point onward the reservation must never
    # be released, even if local consumption persistence fails.
    consume_ministry_skill(
        db,
        request_id=request_id,
    )

    return result
