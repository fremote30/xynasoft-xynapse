"""
Trusted XynaFaith ministry integration routes.

This boundary authenticates the calling XynaFaith service and binds the
external user from trusted server-controlled headers. Ministry skills
generate content only; they do not authorize XynaFaith mutations.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import ValidationError

from xynassist_service.ai.bootstrap import (
    get_configured_model_provider,
)
from xynassist_service.core.security import (
    require_external_user,
    require_service_auth,
)
from xynassist_service.schemas.ministry import (
    MinistryExecuteRequest,
    MinistryExecuteResponse,
)
from xynassist_service.xyniva.ministry_engine import (
    MinistrySkillOutputError,
    execute_ministry_skill,
)


router = APIRouter(
    prefix="/api/v1/integrations/xynafaith/ministry",
    tags=["xynafaith-ministry"],
    dependencies=[
        Depends(require_service_auth),
    ],
)


@router.post(
    "/execute",
    response_model=MinistryExecuteResponse,
)
def execute_ministry(
    request: MinistryExecuteRequest,
    external_user_id: str = Depends(
        require_external_user
    ),
) -> MinistryExecuteResponse:
    """
    Execute one allowlisted provider-independent ministry skill.

    external_user_id is intentionally resolved from the trusted
    integration header and is never accepted in the request body.
    """

    # Resolving the identity is itself part of the trusted boundary.
    # The ministry engine does not currently persist user-specific
    # state, so the identifier is intentionally not forwarded into
    # model input.
    _ = external_user_id

    provider = get_configured_model_provider()

    try:
        result = execute_ministry_skill(
            skill=request.skill,
            payload=request.input,
            provider_name=provider.name,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ministry skill input",
        ) from exc
    except MinistrySkillOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="XynAssist returned invalid ministry output",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ministry skill request",
        ) from exc

    return MinistryExecuteResponse(
        skill=request.skill,
        result=result.model_dump(mode="json"),
    )
