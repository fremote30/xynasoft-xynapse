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
    SavedSermonTransformRequest,
    SavedSermonTransformResponse,
)
from api.services.ministry_skill_metering import (
    UnknownMinistrySkill,
)
from api.services.ministry_skill_service import (
    MinistryExecutionError,
    MinistryExecutionUncertainError,
    execute_ministry_for_user,
    reconcile_ministry_for_user,
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


@router.post(
    "/ministry/sermons/{sermon_id}/transform",
    response_model=SavedSermonTransformResponse,
)
async def transform_saved_sermon(
    sermon_id: int,
    payload: SavedSermonTransformRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transform a persisted sermon owned by the authenticated user.

    The browser controls transformation preferences only. Sermon title,
    scripture, and content are loaded from trusted XynaFaith storage.
    """
    require_ministry_xynassist_enabled()

    from api.services.sermon_persistence import (
        SermonNotFoundError,
        build_sermon_transform_source,
        get_sermon_for_user,
    )

    try:
        sermon = get_sermon_for_user(
            db=db,
            user_id=current_user.id,
            sermon_id=sermon_id,
        )

        source = build_sermon_transform_source(
            sermon
        )

        ministry_input = {
            **source,
            "formats": payload.formats,
            "audience": payload.audience,
            "tone": payload.tone,
            "denomination": payload.denomination,
            "context": payload.context,
        }

        result = await execute_ministry_for_user(
            db,
            user=current_user,
            request_id=str(payload.request_id),
            skill="content.transform",
            payload=ministry_input,
        )

    except SermonNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sermon not found",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

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
            detail="Ministry usage is temporarily unavailable",
        ) from exc

    except MinistryExecutionUncertainError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Ministry request status is uncertain; "
                "check the ministry execution status endpoint "
                "using the same request ID"
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

    return SavedSermonTransformResponse(
        request_id=payload.request_id,
        sermon_id=sermon.id,
        result=result,
    )


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


@router.get(
    "/ministry/executions/{request_id}",
)
async def get_ministry_execution(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recover the status of an existing user-owned ministry execution.

    Does not create a reservation or initiate AI generation.
    """
    from uuid import UUID

    require_ministry_xynassist_enabled()

    try:
        normalized_id = str(UUID(request_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ministry request ID",
        ) from exc

    try:
        return await reconcile_ministry_for_user(
            db,
            user=current_user,
            request_id=normalized_id,
        )

    except MinistryExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ministry execution unavailable",
        ) from exc

    except XynAssistConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ministry recovery temporarily unavailable",
        ) from exc

    except XynAssistError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ministry recovery could not be confirmed",
        ) from exc


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
                "check the ministry execution status endpoint "
                "using the same request ID"
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
