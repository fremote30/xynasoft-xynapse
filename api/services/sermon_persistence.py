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


def build_sermon_update_for_user(
    *,
    db: Session,
    user_id: int,
    sermon_id: int,
    payload: dict[str, Any],
) -> Sermon:
    """
    Update an authenticated user's sermon in the current
    transaction without committing it.

    Ownership always comes from authenticated user context.
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

    return sermon


def build_sermon_delete_for_user(
    *,
    db: Session,
    user_id: int,
    sermon_id: int,
) -> Sermon:
    """
    Delete an authenticated user's sermon in the current
    transaction without committing it.

    Ownership is enforced by the database query using the
    authenticated user context.
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

    db.delete(sermon)

    return sermon



def update_sermon_for_user(
    *,
    db: Session,
    user_id: int,
    sermon_id: int,
    payload: dict[str, Any],
) -> Sermon:
    """
    Persist an update to an authenticated user's sermon.

    This convenience function preserves the existing route
    behavior by owning its commit.
    """
    sermon = build_sermon_update_for_user(
        db=db,
        user_id=user_id,
        sermon_id=sermon_id,
        payload=payload,
    )

    db.commit()
    db.refresh(sermon)

    return sermon


def get_sermon_for_user(
    *,
    db: Session,
    user_id: int,
    sermon_id: int,
) -> Sermon:
    """
    Load one sermon owned by the authenticated user.

    This is the trusted read boundary used by V2 workflows that consume
    persisted sermon content. Ownership comes exclusively from authenticated
    user context and is enforced in the database query.
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

    return sermon


def build_sermon_transform_source(
    sermon: Sermon,
) -> dict[str, str]:
    """
    Build trusted content.transform source fields from a persisted sermon.

    Client-supplied source title, scripture, or sermon content must never be
    used by saved-sermon transformation workflows.
    """
    data = sermon.sermon_data

    if isinstance(data, dict) and data:
        source_content = json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
        )
    elif sermon.content:
        source_content = str(
            sermon.content
        ).strip()
    else:
        source_content = ""

    if not source_content:
        raise ValueError(
            "Sermon has no transformable content"
        )

    return {
        "source_title": (
            sermon.title or ""
        ).strip(),
        "source_scripture": (
            sermon.scripture or ""
        ).strip(),
        "source_content": source_content,
    }


def get_sermon_for_user(
    *,
    db: Session,
    user_id: int,
    sermon_id: int,
) -> Sermon:
    """
    Load one sermon owned by the authenticated user.

    This is the trusted read boundary used by V2 workflows that consume
    persisted sermon content. Ownership comes exclusively from authenticated
    user context and is enforced in the database query.
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

    return sermon


def build_sermon_transform_source(
    sermon: Sermon,
) -> dict[str, str]:
    """
    Build trusted content.transform source fields from a persisted sermon.

    Client-supplied source title, scripture, or sermon content must never be
    used by saved-sermon transformation workflows.
    """
    data = sermon.sermon_data

    if isinstance(data, dict) and data:
        source_content = json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
        )
    elif sermon.content:
        source_content = str(
            sermon.content
        ).strip()
    else:
        source_content = ""

    if not source_content:
        raise ValueError(
            "Sermon has no transformable content"
        )

    return {
        "source_title": (
            sermon.title or ""
        ).strip(),
        "source_scripture": (
            sermon.scripture or ""
        ).strip(),
        "source_content": source_content,
    }
