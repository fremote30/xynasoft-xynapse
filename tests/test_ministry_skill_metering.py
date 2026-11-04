from __future__ import annotations

from types import SimpleNamespace

import pytest

import api.services.ministry_skill_metering as metering
from api.core.entitlements import (
    ENTITLEMENT_BIBLE_STUDY_STUDIO,
    ENTITLEMENT_BIBLICAL_RESEARCH,
    ENTITLEMENT_CONTENT_ENGINE,
    ENTITLEMENT_DEVOTIONAL_STUDIO,
    ENTITLEMENT_SERMON_SERIES,
    ENTITLEMENT_SERMON_STUDIO,
)


class FakeDB:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.mark.parametrize(
    ("skill", "entitlement", "metric"),
    [
        (
            "sermon.generate",
            ENTITLEMENT_SERMON_STUDIO,
            "sermon_generation",
        ),
        (
            "sermon.refine",
            ENTITLEMENT_SERMON_STUDIO,
            "sermon_refinement",
        ),
        (
            "biblical.research",
            ENTITLEMENT_BIBLICAL_RESEARCH,
            "biblical_research",
        ),
        (
            "content.transform",
            ENTITLEMENT_CONTENT_ENGINE,
            "content_generation",
        ),
        (
            "sermon.series.generate",
            ENTITLEMENT_SERMON_SERIES,
            "sermon_series_generation",
        ),
        (
            "bible_study.generate",
            ENTITLEMENT_BIBLE_STUDY_STUDIO,
            "bible_study_generation",
        ),
        (
            "devotional.generate",
            ENTITLEMENT_DEVOTIONAL_STUDIO,
            "devotional_generation",
        ),
    ],
)
def test_ministry_skill_access_mapping(
    skill,
    entitlement,
    metric,
):
    assert metering.ministry_skill_access(skill) == (
        entitlement,
        metric,
    )


def test_unknown_skill_fails_before_reservation(
    monkeypatch,
):
    called = False

    def fake_reserve(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(
        metering,
        "reserve_xyniva_usage",
        fake_reserve,
    )

    with pytest.raises(
        metering.UnknownMinistrySkill
    ):
        metering.reserve_ministry_skill(
            FakeDB(),
            user=SimpleNamespace(id=7),
            request_id="req-1",
            skill="unknown.skill",
        )

    assert called is False


def test_reservation_uses_server_selected_entitlement(
    monkeypatch,
):
    db = FakeDB()
    captured = {}

    def fake_reserve(_db, **kwargs):
        captured.update(kwargs)
        return "reservation"

    monkeypatch.setattr(
        metering,
        "reserve_xyniva_usage",
        fake_reserve,
    )

    result = metering.reserve_ministry_skill(
        db,
        user=SimpleNamespace(id=7),
        request_id="req-2",
        skill="biblical.research",
    )

    assert result == "reservation"
    assert (
        captured["entitlement_key"]
        == ENTITLEMENT_BIBLICAL_RESEARCH
    )
    assert captured["metric"] == "biblical_research"
    assert captured["units"] == 1
    assert db.commits == 1
    assert db.rollbacks == 0


def test_reservation_failure_rolls_back(
    monkeypatch,
):
    db = FakeDB()

    def fake_reserve(*args, **kwargs):
        raise RuntimeError("denied")

    monkeypatch.setattr(
        metering,
        "reserve_xyniva_usage",
        fake_reserve,
    )

    with pytest.raises(RuntimeError):
        metering.reserve_ministry_skill(
            db,
            user=SimpleNamespace(id=7),
            request_id="req-3",
            skill="sermon.generate",
        )

    assert db.commits == 0
    assert db.rollbacks == 1


def test_consume_commits(monkeypatch):
    db = FakeDB()

    monkeypatch.setattr(
        metering,
        "complete_xyniva_usage",
        lambda *args, **kwargs: "consumed",
    )

    result = metering.consume_ministry_skill(
        db,
        request_id="req-4",
    )

    assert result == "consumed"
    assert db.commits == 1
    assert db.rollbacks == 0


def test_release_commits(monkeypatch):
    db = FakeDB()

    monkeypatch.setattr(
        metering,
        "release_xyniva_usage",
        lambda *args, **kwargs: "released",
    )

    result = metering.release_ministry_skill(
        db,
        request_id="req-5",
    )

    assert result == "released"
    assert db.commits == 1
    assert db.rollbacks == 0
