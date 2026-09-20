"""
Authenticated XynaFaith V2 ministry intelligence boundary.

The browser selects only:
- a request identity
- an exposed ministry skill
- that skill's input

XynaFaith controls commercial access, quota accounting, trusted
XynAssist identity, and integration credentials.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from api.core.config import XYNASSIST_ENABLED
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.user import User
from api.schemas.ministry import (
    MinistryExecuteRequest,
    MinistryExecuteResponse,
)
from api.services.ministry_skill_metering import (
    UnknownMinistrySkill,
)
from api.services.ministry_skill_service import (
    MinistryExecutionUncertainError,
    execute_ministry_for_user,
)
from api.services.xynassist_client import (
    XynAssistConfigurationError,
    XynAssistError,
)
from api.services.xyniva_usage_service import (
    XynivaUsageConfigurationError,
    XynivaUsageDenied,
)


router = APIRouter()


def require_ministry_xynassist_enabled() -> None:
    """
    V2 ministry intelligence fails closed.

    Unlike the legacy V1 sermon route, this boundary never falls back
    to a second AI implementation.
    """

    if not XYNASSIST_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "XynAssist ministry intelligence "
                "is temporarily unavailable"
            ),
        )


@router.post(
    "/ministry/execute",
    response_model=MinistryExecuteResponse,
)
async def execute_ministry(
    payload: MinistryExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_ministry_xynassist_enabled()

    try:
        result = await execute_ministry_for_user(
            db,
            user=current_user,
            request_id=str(payload.request_id),
            skill=payload.skill,
            payload=payload.input,
        )

    except UnknownMinistrySkill as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported ministry skill",
        ) from exc

    except XynivaUsageDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ministry feature is not available",
        ) from exc

    except XynivaUsageConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Ministry usage is temporarily "
                "unavailable"
            ),
        ) from exc

    except MinistryExecutionUncertainError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Ministry request status is uncertain; "
                "retry with the same request ID"
            ),
        ) from exc

    except XynAssistConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "XynAssist ministry intelligence "
                "is temporarily unavailable"
            ),
        ) from exc

    except XynAssistError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ministry intelligence request failed",
        ) from exc

    return MinistryExecuteResponse(
        request_id=payload.request_id,
        skill=payload.skill,
        result=result,
    )
