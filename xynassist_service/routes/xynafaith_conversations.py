"""
Trusted XynaFaith integration routes for XynAssist conversations.
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
)
from xynassist_service.db.database import get_db
from xynassist_service.schemas.conversations import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
)
from xynassist_service.services.conversations import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
)


router = APIRouter(
    prefix=(
        "/api/v1/integrations/"
        "xynafaith/conversations"
    ),
    tags=["XynaFaith Integration"],
    dependencies=[
        Depends(require_service_auth),
    ],
)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_route(
    payload: ConversationCreate,
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    return create_conversation(
        db,
        external_user_id=external_user_id,
        title=payload.title,
    )


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def list_conversations_route(
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    return list_conversations(
        db,
        external_user_id=external_user_id,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation_route(
    conversation_id: str,
    external_user_id: str = Depends(
        require_external_user
    ),
    db: Session = Depends(get_db),
):
    conversation = get_conversation(
        db,
        external_user_id=external_user_id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = list_messages(
        db,
        conversation_id=conversation.id,
    )

    return ConversationDetailResponse(
        id=conversation.id,
        product=conversation.product,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )
