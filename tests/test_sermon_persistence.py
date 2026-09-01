import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from api.services.sermon_persistence import (
    SermonNotFoundError,
    save_sermon_for_user,
    update_sermon_for_user,
)


def test_save_sermon_uses_authenticated_user_as_owner():
    db = MagicMock()

    payload = {
        "title": "The Word Is Near",
        "scripture": "Romans 10",
        "introduction": "Introduction",
        "main_points": [],
        "application": "Application",
        "conclusion": "Conclusion",
        # Must never control ownership.
        "author_id": 999,
    }

    sermon = save_sermon_for_user(
        db=db,
        user_id=123,
        payload=payload,
    )

    assert sermon.author_id == 123
    assert sermon.title == "The Word Is Near"
    assert sermon.scripture == "Romans 10"
    assert sermon.sermon_data == payload
    assert json.loads(sermon.content) == payload
    assert sermon.is_public == 0

    db.add.assert_called_once_with(
        sermon
    )
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(
        sermon
    )


def test_update_sermon_requires_authenticated_owner():
    db = MagicMock()

    sermon = SimpleNamespace(
        id=42,
        author_id=123,
        title="Old title",
        scripture="Romans 10",
        content=None,
        sermon_data=None,
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = sermon

    payload = {
        "title": "Updated title",
        "scripture": "Romans 10:1-17",
        "main_points": [],
    }

    result = update_sermon_for_user(
        db=db,
        user_id=123,
        sermon_id=42,
        payload=payload,
    )

    assert result is sermon
    assert sermon.title == "Updated title"
    assert sermon.scripture == "Romans 10:1-17"
    assert sermon.sermon_data == payload
    assert json.loads(
        sermon.content
    ) == payload

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(
        sermon
    )


def test_update_sermon_fails_closed_when_not_owned():
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    with pytest.raises(
        SermonNotFoundError
    ):
        update_sermon_for_user(
            db=db,
            user_id=123,
            sermon_id=42,
            payload={
                "title": "Attempted update",
            },
        )

    db.commit.assert_not_called()
    db.refresh.assert_not_called()
