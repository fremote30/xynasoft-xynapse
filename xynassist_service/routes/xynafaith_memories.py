"""
Trusted XynaFaith integration routes for XynAssist memory.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from xynassist_service.core.security import (
    require_external_user,
    require_service_auth,
)
from xynassist_service.db.database import get_db
from xynassist_service.schemas.memories import (
    MemoryCreate,
    MemoryResponse,
    MemoryUpdate,
)
from xynassist_service.services.memories import (
    create_or_update_memory,
    deactivate_memory,
    list_active_memories,
    update_memory_value,
)


PRODUCT = "xynafaith"


router = APIRouter(
    prefix=(
        "/api/v1/integrations/"
        "xynafaith/memories"
    ),
    tags=["XynaFaith Integration"],
    dependencies=[
        Depends(require_service_auth),
    ],
)


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_200_OK,
)
def create_memory_route(
    payload: MemoryCreate,
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    try:
        memory = create_or_update_memory(
            db,
            external_user_id=external_user_id,
            product=PRODUCT,
            memory_type=payload.memory_type,
            key=payload.key,
            value=payload.value,
            source="explicit_user",
        )

        db.commit()
        db.refresh(memory)

        return memory

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[MemoryResponse],
)
def list_memories_route(
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    return list_active_memories(
        db,
        external_user_id=external_user_id,
        product=PRODUCT,
    )


@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
)
def update_memory_route(
    memory_id: str,
    payload: MemoryUpdate,
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    try:
        memory = update_memory_value(
            db,
            external_user_id=external_user_id,
            memory_id=memory_id,
            value=payload.value,
            product=PRODUCT,
        )

        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )

        db.commit()
        db.refresh(memory)

        return memory

    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def forget_memory_route(
    memory_id: str,
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    try:
        changed = deactivate_memory(
            db,
            external_user_id=external_user_id,
            memory_id=memory_id,
            product=PRODUCT,
        )

        if not changed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )

        db.commit()

        return Response(
            status_code=status.HTTP_204_NO_CONTENT
        )

    except HTTPException:
        db.rollback()
        raise
