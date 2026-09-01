import json
from typing import Any

from sqlalchemy.orm import Session

from api.models.sermon import Sermon


class SermonNotFoundError(Exception):
    """Raised when a sermon is not owned by the requested user."""


def build_sermon_for_user(
    *,
    db: Session,
    user_id: int,
    payload: dict[str, Any],
) -> Sermon:
    """
    Add a new authenticated user's sermon to the current
    transaction without committing it.

    Ownership always comes from authenticated user context,
    never from the sermon payload.
    """
    sermon = Sermon(
        title=payload.get(
            "title",
            "Untitled Sermon",
        ),
        scripture=payload.get(
            "scripture",
        ),
        author_id=user_id,
        content=json.dumps(
            payload,
        ),
        sermon_data=payload,
        is_public=0,
    )

    db.add(sermon)

    # Allocate database-generated values such as sermon.id
    # while preserving the caller's transaction boundary.
    db.flush()

    return sermon


def save_sermon_for_user(
    *,
    db: Session,
    user_id: int,
    payload: dict[str, Any],
) -> Sermon:
    """
    Persist a new sermon for an authenticated XynaFaith user.

    This convenience function preserves the existing
    save-route behavior by owning its commit.
    """
    sermon = build_sermon_for_user(
        db=db,
        user_id=user_id,
        payload=payload,
    )

    db.commit()
    db.refresh(sermon)

    return sermon


def update_sermon_for_user(
    *,
    db: Session,
    user_id: int,
    sermon_id: int,
    payload: dict[str, Any],
) -> Sermon:
    """
    Update an existing sermon only when it belongs to the
    authenticated XynaFaith user.
    """
    sermon = (
        db.query(Sermon)
        .filter(
            Sermon.id == sermon_id,
        )
        .filter(
            Sermon.author_id == user_id,
        )
        .first()
    )

    if sermon is None:
        raise SermonNotFoundError(
            "Sermon not found"
        )

    sermon.title = payload.get(
        "title",
        sermon.title,
    )

    sermon.scripture = payload.get(
        "scripture",
        sermon.scripture,
    )

    sermon.content = json.dumps(
        payload,
    )

    sermon.sermon_data = payload

    db.commit()
    db.refresh(sermon)

    return sermon
