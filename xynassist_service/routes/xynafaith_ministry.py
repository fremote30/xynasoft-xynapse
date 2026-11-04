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
from sqlalchemy.orm import Session

from xynassist_service.ai.bootstrap import (
    get_configured_model_provider,
)
from xynassist_service.core.security import (
    require_external_user,
    require_service_auth,
)
from xynassist_service.db.database import get_db
from xynassist_service.schemas.ministry import (
    MinistryExecuteRequest,
    MinistryExecuteResponse,
)
from xynassist_service.services.ai_execution_telemetry import (
    record_ai_execution,
)
from xynassist_service.services.ministry_idempotency import (
    MinistryLeaseLost,
    MinistryRequestConflict,
    MinistryRequestInProgress,
    MinistryRequestStateError,
    claim_ministry_request,
    complete_ministry_request,
    fail_ministry_request,
    require_ministry_lease,
)
from xynassist_service.xyniva.ministry_engine import (
    MinistrySkillOutputError,
    execute_ministry_skill_with_telemetry,
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
    db: Session = Depends(get_db),
) -> MinistryExecuteResponse:
    """
    Execute one durable logical ministry request.

    Completed retries replay the persisted result without invoking
    the configured model provider again.
    """

    try:
        claim = claim_ministry_request(
            db,
            product="xynafaith",
            external_user_id=external_user_id,
            request_id=request.request_id,
            skill=request.skill,
            payload=request.input,
        )
    except MinistryRequestConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "request_id was already used "
                "for different ministry input"
            ),
        ) from exc
    except MinistryRequestInProgress as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ministry request is already processing",
        ) from exc
    except MinistryRequestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ministry request cannot be replayed",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if claim.is_replay:
        return MinistryExecuteResponse(
            skill=request.skill,
            result=claim.replay_result,
        )

    execution_id = claim.execution.id
    lease_token = claim.lease_token

    # Persist the processing claim before expensive AI work.
    db.commit()

    provider = get_configured_model_provider()

    try:
        model_execution = execute_ministry_skill_with_telemetry(
            skill=request.skill,
            payload=request.input,
            provider_name=provider.name,
        )
        result = model_execution.result
    except ValidationError as exc:
        try:
            execution = require_ministry_lease(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                request_id=request.request_id,
                execution_id=execution_id,
                lease_token=lease_token,
            )
            fail_ministry_request(
                db,
                execution=execution,
                lease_token=lease_token,
                error_code="invalid_skill_input",
            )
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ministry skill input",
        ) from exc
    except MinistrySkillOutputError as exc:
        try:
            execution = require_ministry_lease(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                request_id=request.request_id,
                execution_id=execution_id,
                lease_token=lease_token,
            )
            if exc.provider and exc.model:
                record_ai_execution(
                    db,
                    product="xynafaith",
                    external_user_id=external_user_id,
                    request_id=request.request_id,
                    operation=request.skill,
                    provider=exc.provider,
                    model=exc.model,
                    input_tokens=exc.input_tokens,
                    output_tokens=exc.output_tokens,
                    attempt_number=int(
                        execution.attempt_count or 1
                    ),
                )

            fail_ministry_request(
                db,
                execution=execution,
                lease_token=lease_token,
                error_code="invalid_skill_output",
            )
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="XynAssist returned invalid ministry output",
        ) from exc
    except ValueError as exc:
        try:
            execution = require_ministry_lease(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                request_id=request.request_id,
                execution_id=execution_id,
                lease_token=lease_token,
            )
            fail_ministry_request(
                db,
                execution=execution,
                lease_token=lease_token,
                error_code="invalid_skill_request",
            )
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ministry skill request",
        ) from exc
    except Exception:
        try:
            execution = require_ministry_lease(
                db,
                product="xynafaith",
                external_user_id=external_user_id,
                request_id=request.request_id,
                execution_id=execution_id,
                lease_token=lease_token,
            )
            fail_ministry_request(
                db,
                execution=execution,
                lease_token=lease_token,
                error_code="ministry_engine_failure",
            )
            db.commit()
        except Exception:
            db.rollback()

        raise

    result_payload = result.model_dump(mode="json")

    try:
        execution = require_ministry_lease(
            db,
            product="xynafaith",
            external_user_id=external_user_id,
            request_id=request.request_id,
            execution_id=execution_id,
            lease_token=lease_token,
        )

        record_ai_execution(
            db,
            product="xynafaith",
            external_user_id=external_user_id,
            request_id=request.request_id,
            operation=request.skill,
            provider=model_execution.provider,
            model=model_execution.model,
            input_tokens=model_execution.input_tokens,
            output_tokens=model_execution.output_tokens,
            attempt_number=int(
                execution.attempt_count or 1
            ),
        )

        complete_ministry_request(
            db,
            execution=execution,
            lease_token=lease_token,
            result=result_payload,
        )

        db.commit()
    except MinistryLeaseLost as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ministry execution lease was lost",
        ) from exc
    except Exception:
        db.rollback()
        raise

    return MinistryExecuteResponse(
        skill=request.skill,
        result=result_payload,
    )
