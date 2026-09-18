from __future__ import annotations

from typing import Any
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from api.core.config import XYNASSIST_ENABLED
from api.core.dependencies import (
    get_current_user,
    get_db,
)
from sqlalchemy.orm import Session

from api.models.user import User
from api.services.conversation_actions import (
    ConversationActionContextError,
    UnsupportedConversationActionError,
    execute_conversation_action,
)
from api.services.conversation_pending_actions import (
    ConversationPendingActionError,
    SERMON_DELETE_ACTION,
    get_pending_sermon_delete,
    record_pending_sermon_delete,
)
from api.services.conversation_pending_memory_actions import (
    ConversationPendingMemoryActionError,
    MEMORY_FORGET_ACTION,
    consume_pending_memory_forget,
    get_pending_memory_forget,
    record_pending_memory_forget,
)
from api.services.ai_usage_metering import (
    UsageLimitExceeded,
    UsageMeteringError,
)
from api.services.xynassist_client import (
    XynAssistClient,
    XynAssistConflictError,
    XynAssistError,
    XynAssistRequestInProgressError,
    XynAssistRequestStateError,
)
from api.services.xyniva_turn_metering import (
    consume_conversation_turn,
    release_conversation_turn,
    reserve_conversation_turn,
)
from api.services.xyniva_usage_service import (
    XynivaUsageConfigurationError,
    XynivaUsageDenied,
)


router = APIRouter()


MEMORY_REMEMBER_ACTION = "memory.remember"
MEMORY_TYPES = frozenset({
    "preference",
    "ministry_context",
    "user_fact",
})


def _validated_memory_action_arguments(
    action: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    """Validate an XynAssist memory proposal at the product boundary."""

    action_name = action.get("name")

    if action_name not in {
        MEMORY_REMEMBER_ACTION,
        MEMORY_FORGET_ACTION,
    }:
        raise ValueError("Unsupported memory action")

    arguments = action.get("arguments")

    if not isinstance(arguments, dict):
        raise ValueError("Invalid memory action arguments")

    expected_keys = {"memory_type", "key"}

    if action_name == MEMORY_REMEMBER_ACTION:
        expected_keys.add("value")

    if set(arguments) != expected_keys:
        raise ValueError("Invalid memory action arguments")

    memory_type = arguments.get("memory_type")
    memory_key = arguments.get("key")

    if memory_type not in MEMORY_TYPES:
        raise ValueError("Invalid memory action arguments")

    if (
        not isinstance(memory_key, str)
        or not memory_key.strip()
        or len(memory_key.strip()) > 255
    ):
        raise ValueError("Invalid memory action arguments")

    validated = {
        "memory_type": memory_type,
        "key": memory_key.strip(),
    }

    if action_name == MEMORY_REMEMBER_ACTION:
        memory_value = arguments.get("value")

        if (
            not isinstance(memory_value, str)
            or not memory_value.strip()
        ):
            raise ValueError("Invalid memory action arguments")

        validated["value"] = memory_value.strip()

    return action_name, validated


def _memory_action_request_id(
    *,
    user_id: int,
    conversation_id: str,
    turn_request_id: str,
    action_name: str,
) -> str:
    """Derive a stable execution identity for an immediate memory action."""

    identity = (
        "xynafaith:memory-action:"
        f"{user_id}:"
        f"{conversation_id}:"
        f"{turn_request_id}:"
        f"{action_name}"
    )

    return str(uuid5(NAMESPACE_URL, identity))


def require_xynassist_enabled() -> None:
    """
    Fail closed when the shared XynAssist conversation service
    is intentionally disabled.

    The check occurs before any remote call or AI quota
    reservation so disabled infrastructure cannot consume usage.
    """

    if not XYNASSIST_ENABLED:
        raise HTTPException(
            status_code=503,
            detail=(
                "Conversation service is "
                "temporarily unavailable"
            ),
        )


class ConversationCreate(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=255,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ConversationSermonContext(BaseModel):
    """
    Current XynaFaith sermon state supplied for a
    conversational sermon action.

    Identity and ownership are intentionally absent.
    """

    id: int | None = Field(
        default=None,
        ge=1,
    )

    data: dict[str, Any]

    model_config = ConfigDict(
        extra="forbid",
    )


class ConversationTurnCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=50_000,
    )

    request_id: UUID

    sermon: ConversationSermonContext | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


def conversation_service_unavailable(
    exc: XynAssistError,
) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "Conversation service is "
            "temporarily unavailable"
        ),
    )


def conversation_usage_unavailable(
    exc: Exception,
) -> HTTPException:
    """
    Convert internal entitlement/metering failures into the
    public conversation API contract without exposing billing
    or quota internals.
    """

    if isinstance(exc, XynivaUsageDenied):
        return HTTPException(
            status_code=403,
            detail="Xyniva is not available for this account",
        )

    if isinstance(exc, UsageLimitExceeded):
        return HTTPException(
            status_code=429,
            detail="Xyniva usage limit reached",
        )

    if isinstance(
        exc,
        (
            XynivaUsageConfigurationError,
            UsageMeteringError,
        ),
    ):
        return HTTPException(
            status_code=503,
            detail=(
                "Xyniva usage service is "
                "temporarily unavailable"
            ),
        )

    return HTTPException(
        status_code=500,
        detail="Xyniva usage could not be recorded",
    )


@router.post(
    "/conversations",
    status_code=201,
)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(
        get_current_user
    ),
):
    require_xynassist_enabled()

    try:
        return await XynAssistClient().create_conversation(
            external_user_id=str(
                current_user.id
            ),
            title=payload.title,
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc


@router.get(
    "/conversations",
)
async def list_conversations(
    current_user: User = Depends(
        get_current_user
    ),
):
    require_xynassist_enabled()

    try:
        return await XynAssistClient().list_conversations(
            external_user_id=str(
                current_user.id
            ),
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc


@router.get(
    "/conversations/{conversation_id}",
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(
        get_current_user
    ),
):
    require_xynassist_enabled()

    try:
        return await XynAssistClient().get_conversation(
            external_user_id=str(
                current_user.id
            ),
            conversation_id=conversation_id,
        )
    except XynAssistError as exc:
        raise conversation_service_unavailable(
            exc
        ) from exc


@router.post(
    "/conversations/{conversation_id}/turns",
)
async def execute_conversation_turn(
    conversation_id: str,
    payload: ConversationTurnCreate,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    require_xynassist_enabled()

    sermon_context = payload.sermon

    trusted_context = None
    pending = None

    if sermon_context is not None:
        trusted_context = {
            "active_resource": "sermon",
            "resource_persisted": (
                sermon_context.id is not None
            ),
        }

        pending = get_pending_sermon_delete(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            sermon_id=sermon_context.id,
        )

        if pending is not None:
            trusted_context["pending_action"] = (
                SERMON_DELETE_ACTION
            )

    pending_memory = get_pending_memory_forget(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if pending_memory is not None:
        if trusted_context is None:
            trusted_context = {}

        trusted_context["pending_memory_action"] = (
            MEMORY_FORGET_ACTION
        )

    request_id = str(payload.request_id)

    # Reserve quota and commit it before the expensive external
    # XynAssist call. This prevents concurrent requests from
    # overspending the same allowance.
    try:
        reserve_conversation_turn(
            db,
            user=current_user,
            request_id=request_id,
        )
    except Exception as exc:
        raise conversation_usage_unavailable(
            exc
        ) from exc

    try:
        result = (
            await XynAssistClient()
            .execute_conversation_turn(
                external_user_id=str(
                    current_user.id
                ),
                conversation_id=conversation_id,
                request_id=request_id,
                content=payload.content,
                context=trusted_context,
            )
        )
    except XynAssistRequestInProgressError as exc:
        # The remote operation may already be executing. Releasing
        # quota here could allow the same logical work to be spent
        # twice while the first execution is still in flight.
        raise HTTPException(
            status_code=409,
            detail=(
                "This conversation request is already "
                "being processed"
            ),
        ) from exc
    except XynAssistRequestStateError as exc:
        # Failed/non-replayable remote requests remain fail-closed.
        # A new logical attempt must use a new request identifier.
        raise HTTPException(
            status_code=409,
            detail=(
                "This conversation request cannot be "
                "replayed; start a new request"
            ),
        ) from exc
    except XynAssistConflictError as exc:
        # A conflicting identifier can belong to work that already
        # completed and consumed quota. Never release usage here.
        raise HTTPException(
            status_code=409,
            detail=(
                "This request identifier was already used "
                "for a different conversation turn"
            ),
        ) from exc
    except XynAssistError as exc:
        # The external AI operation did not complete successfully,
        # so return the reservation to the user's allowance.
        try:
            release_conversation_turn(
                db,
                request_id=request_id,
            )
        except Exception as release_exc:
            raise conversation_usage_unavailable(
                release_exc
            ) from release_exc

        raise conversation_service_unavailable(
            exc
        ) from exc
    except Exception:
        # Unexpected failures before a successful AI response must
        # also return reserved quota.
        try:
            release_conversation_turn(
                db,
                request_id=request_id,
            )
        except Exception as release_exc:
            raise conversation_usage_unavailable(
                release_exc
            ) from release_exc

        raise

    # XynAssist successfully produced a turn. Usage is consumed
    # before processing any optional local product action. If a
    # later product mutation fails, the AI work was still performed
    # and must remain consumed.
    try:
        consume_conversation_turn(
            db,
            request_id=request_id,
        )
    except Exception as exc:
        raise conversation_usage_unavailable(
            exc
        ) from exc

    action = result.get(
        "action"
    )

    if action is None:
        return result

    if not isinstance(action, dict):
        raise HTTPException(
            status_code=502,
            detail=(
                "Conversation service returned "
                "an invalid action"
            ),
        )

    source_message_id = result.get(
        "user_message_id"
    )

    if (
        not isinstance(source_message_id, str)
        or not source_message_id.strip()
        or len(source_message_id.strip()) > 255
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Conversation service returned "
                "an invalid action"
            ),
        )

    action_name = action.get("name")

    if action_name in {
        MEMORY_REMEMBER_ACTION,
        MEMORY_FORGET_ACTION,
    }:
        try:
            (
                memory_action_name,
                memory_arguments,
            ) = _validated_memory_action_arguments(action)
        except ValueError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Conversation service returned "
                    "an invalid memory action"
                ),
            ) from exc

        prompt = result.get("prompt")

        if memory_action_name == MEMORY_REMEMBER_ACTION:
            if prompt is not None:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Conversation service returned "
                        "an invalid memory confirmation"
                    ),
                )

            try:
                executed_action = (
                    await XynAssistClient()
                    .execute_memory_action(
                        external_user_id=str(
                            current_user.id
                        ),
                        request_id=_memory_action_request_id(
                            user_id=current_user.id,
                            conversation_id=conversation_id,
                            turn_request_id=request_id,
                            action_name=memory_action_name,
                        ),
                        action_name=memory_action_name,
                        arguments=memory_arguments,
                        trusted_confirmed=False,
                    )
                )
            except XynAssistError as exc:
                raise conversation_service_unavailable(
                    exc
                ) from exc

            result["action"] = executed_action
            return result

        if prompt is None:
            if pending_memory is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "memory.forget requires trusted "
                        "pending confirmation"
                    ),
                )

            if (
                memory_arguments["memory_type"]
                != pending_memory.memory_type
                or memory_arguments["key"]
                != pending_memory.memory_key
            ):
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Conversation memory confirmation "
                        "does not match pending action"
                    ),
                )

            pending_arguments = {
                "memory_type": pending_memory.memory_type,
                "key": pending_memory.memory_key,
            }

            try:
                executed_action = (
                    await XynAssistClient()
                    .execute_memory_action(
                        external_user_id=str(
                            current_user.id
                        ),
                        request_id=(
                            pending_memory.action_request_id
                        ),
                        action_name=MEMORY_FORGET_ACTION,
                        arguments=pending_arguments,
                        trusted_confirmed=True,
                    )
                )

                consume_pending_memory_forget(
                    db=db,
                    pending=pending_memory,
                )
                db.commit()

            except XynAssistError as exc:
                db.rollback()

                raise conversation_service_unavailable(
                    exc
                ) from exc

            except Exception as exc:
                db.rollback()

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Conversation memory action could "
                        "not be completed"
                    ),
                ) from exc

            result["action"] = executed_action
            return result

        if (
            not isinstance(prompt, str)
            or not prompt.strip()
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Conversation service returned "
                    "an invalid memory confirmation"
                ),
            )

        normalized_source_message_id = (
            source_message_id.strip()
        )

        same_pending_proposal = (
            pending_memory is not None
            and pending_memory.memory_type
            == memory_arguments["memory_type"]
            and pending_memory.memory_key
            == memory_arguments["key"]
            and pending_memory.source_message_id
            == normalized_source_message_id
        )

        if same_pending_proposal:
            action_request_id = (
                pending_memory.action_request_id
            )
        else:
            action_request_id = str(uuid4())

        try:
            record_pending_memory_forget(
                db=db,
                user_id=current_user.id,
                conversation_id=conversation_id,
                memory_type=memory_arguments[
                    "memory_type"
                ],
                memory_key=memory_arguments["key"],
                source_message_id=(
                    normalized_source_message_id
                ),
                action_request_id=action_request_id,
            )
            db.commit()
        except ConversationPendingMemoryActionError as exc:
            db.rollback()

            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Conversation confirmation could not "
                    "be recorded"
                ),
            ) from exc

        return result

    # Confirmation-required actions are pending state, not
    # executable product mutations. Bind the request to the
    # exact authenticated product resource before returning
    # the confirmation prompt to the browser.
    prompt = result.get("prompt")

    if prompt is not None:
        if (
            not isinstance(prompt, str)
            or not prompt.strip()
            or action.get("name")
            != SERMON_DELETE_ACTION
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Conversation service returned "
                    "an invalid confirmation"
                ),
            )

        try:
            record_pending_sermon_delete(
                db=db,
                user_id=current_user.id,
                conversation_id=conversation_id,
                sermon_id=(
                    sermon_context.id
                    if sermon_context
                    else None
                ),
                source_message_id=source_message_id,
            )
        except ConversationPendingActionError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Conversation confirmation could not "
                    "be recorded"
                ),
            ) from exc

        return result

    try:
        executed_action = execute_conversation_action(
            db=db,
            user_id=current_user.id,
            request_id=request_id,
            source_message_id=source_message_id,
            action=action,
            sermon_id=(
                sermon_context.id
                if sermon_context
                else None
            ),
            sermon_data=(
                sermon_context.data
                if sermon_context
                else None
            ),
            bound_sermon_id=(
                pending.resource_id
                if (
                    action.get("name")
                    == SERMON_DELETE_ACTION
                    and pending is not None
                )
                else None
            ),
            pending_action=(
                pending
                if (
                    action.get("name")
                    == SERMON_DELETE_ACTION
                    and pending is not None
                )
                else None
            ),
        )
    except (
        UnsupportedConversationActionError,
        ConversationActionContextError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Conversation action could not "
                "be completed"
            ),
        ) from exc

    return {
        **result,
        "action": executed_action,
    }
