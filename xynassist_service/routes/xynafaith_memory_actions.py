"""
Trusted XynaFaith integration route for XynAssist-owned memory actions.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from xynassist_service.core.security import (
    require_external_user,
    require_service_auth,
    require_trusted_action_confirmation,
)
from xynassist_service.db.database import get_db
from xynassist_service.schemas.memory_actions import (
    MemoryActionExecuteRequest,
    MemoryActionExecuteResponse,
)
from xynassist_service.services.action_executions import (
    ActionExecutionConflict,
    ActionExecutionStateError,
)
from xynassist_service.services.memory_actions import (
    MemoryActionConfirmationRequired,
    MemoryActionTargetNotFound,
    execute_memory_action,
)


PRODUCT = "xynafaith"


router = APIRouter(
    prefix=(
        "/api/v1/integrations/"
        "xynafaith/memory-actions"
    ),
    tags=["XynaFaith Integration"],
    dependencies=[
        Depends(require_service_auth),
    ],
)


@router.post(
    "/execute",
    response_model=MemoryActionExecuteResponse,
    status_code=status.HTTP_200_OK,
)
def execute_memory_action_route(
    payload: MemoryActionExecuteRequest,
    external_user_id: str = Depends(
        require_external_user
    ),
    trusted_confirmed: bool = Depends(
        require_trusted_action_confirmation
    ),
    db: Session = Depends(get_db),
):
    try:
        result = execute_memory_action(
            db,
            product=PRODUCT,
            external_user_id=external_user_id,
            request_id=payload.request_id,
            action_name=payload.action_name,
            arguments=payload.arguments,
            trusted_confirmed=trusted_confirmed,
        )

        db.commit()

        return result

    except MemoryActionConfirmationRequired as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except MemoryActionTargetNotFound as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ActionExecutionConflict as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ActionExecutionStateError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise
