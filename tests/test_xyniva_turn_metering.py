from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from api.services.xyniva_turn_metering import (
    XYNIVA_CHAT_ENTITLEMENT,
    XYNIVA_CHAT_METRIC,
    consume_conversation_turn,
    release_conversation_turn,
    reserve_conversation_turn,
)


def _user():
    return SimpleNamespace(id=7, role="member")


def test_reserve_turn_uses_xyniva_chat_and_commits():
    db = Mock()
    reservation = SimpleNamespace(request_id="req-1")

    with patch(
        "api.services.xyniva_turn_metering.reserve_xyniva_usage",
        return_value=reservation,
    ) as reserve_mock:
        result = reserve_conversation_turn(
            db,
            user=_user(),
            request_id="req-1",
        )

    assert result is reservation

    reserve_mock.assert_called_once_with(
        db,
        user=reserve_mock.call_args.kwargs["user"],
        request_id="req-1",
        entitlement_key=XYNIVA_CHAT_ENTITLEMENT,
        metric=XYNIVA_CHAT_METRIC,
        units=1,
        church_id=None,
        now=None,
    )

    assert reserve_mock.call_args.kwargs["user"].id == 7
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()


def test_reserve_turn_preserves_explicit_church_context():
    db = Mock()

    with patch(
        "api.services.xyniva_turn_metering.reserve_xyniva_usage",
        return_value=SimpleNamespace(request_id="req-2"),
    ) as reserve_mock:
        reserve_conversation_turn(
            db,
            user=_user(),
            request_id="req-2",
            church_id=44,
        )

    assert reserve_mock.call_args.kwargs["church_id"] == 44
    db.commit.assert_called_once_with()


def test_reserve_turn_rolls_back_when_reservation_fails():
    db = Mock()

    with patch(
        "api.services.xyniva_turn_metering.reserve_xyniva_usage",
        side_effect=RuntimeError("reservation failed"),
    ):
        with pytest.raises(
            RuntimeError,
            match="reservation failed",
        ):
            reserve_conversation_turn(
                db,
                user=_user(),
                request_id="req-3",
            )

    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()


def test_reserve_turn_rolls_back_when_commit_fails():
    db = Mock()
    db.commit.side_effect = RuntimeError("commit failed")

    with patch(
        "api.services.xyniva_turn_metering.reserve_xyniva_usage",
        return_value=SimpleNamespace(request_id="req-4"),
    ):
        with pytest.raises(
            RuntimeError,
            match="commit failed",
        ):
            reserve_conversation_turn(
                db,
                user=_user(),
                request_id="req-4",
            )

    db.rollback.assert_called_once_with()


def test_consume_turn_commits():
    db = Mock()
    reservation = SimpleNamespace(request_id="req-5")

    with patch(
        "api.services.xyniva_turn_metering.complete_xyniva_usage",
        return_value=reservation,
    ) as complete_mock:
        result = consume_conversation_turn(
            db,
            request_id="req-5",
        )

    assert result is reservation

    complete_mock.assert_called_once_with(
        db,
        request_id="req-5",
        now=None,
    )

    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()


def test_consume_turn_rolls_back_on_failure():
    db = Mock()

    with patch(
        "api.services.xyniva_turn_metering.complete_xyniva_usage",
        side_effect=RuntimeError("consume failed"),
    ):
        with pytest.raises(
            RuntimeError,
            match="consume failed",
        ):
            consume_conversation_turn(
                db,
                request_id="req-6",
            )

    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()


def test_release_turn_commits():
    db = Mock()
    reservation = SimpleNamespace(request_id="req-7")

    with patch(
        "api.services.xyniva_turn_metering.release_xyniva_usage",
        return_value=reservation,
    ) as release_mock:
        result = release_conversation_turn(
            db,
            request_id="req-7",
        )

    assert result is reservation

    release_mock.assert_called_once_with(
        db,
        request_id="req-7",
        now=None,
    )

    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()


def test_release_turn_rolls_back_on_failure():
    db = Mock()

    with patch(
        "api.services.xyniva_turn_metering.release_xyniva_usage",
        side_effect=RuntimeError("release failed"),
    ):
        with pytest.raises(
            RuntimeError,
            match="release failed",
        ):
            release_conversation_turn(
                db,
                request_id="req-8",
            )

    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()
