from unittest.mock import MagicMock

import pytest

from api.core.pricing_catalog import CatalogPrice
from api.services.pricing_catalog_sync import PricingCatalogSyncResult
from scripts import sync_pricing_catalog as command


def _result():
    return PricingCatalogSyncResult(
        prices_created=4,
        prices_transitioned=2,
        prices_unchanged=3,
    )


def _catalog():
    return (
        CatalogPrice(
            plan_code="pastor_pro",
            market_code="GH",
            currency="GHS",
            billing_interval="monthly",
            amount_minor=10000,
        ),
    )


def test_parser_defaults_to_dry_run():
    args = command.build_parser().parse_args([])
    assert args.commit is False


def test_parser_accepts_explicit_commit():
    args = command.build_parser().parse_args(["--commit"])
    assert args.commit is True


def test_dry_run_uses_approved_catalog_and_rolls_back(monkeypatch):
    db = MagicMock()
    approved_catalog = _catalog()
    observed = {}

    monkeypatch.setattr(command, "SessionLocal", lambda: db)
    monkeypatch.setattr(command, "APPROVED_PRICING_CATALOG", approved_catalog)

    def fake_sync(session, prices):
        observed["session"] = session
        observed["prices"] = prices
        return _result()

    monkeypatch.setattr(command, "sync_pricing_catalog", fake_sync)

    result = command.run(commit=False)

    assert result == _result()
    assert observed["session"] is db
    assert observed["prices"] is approved_catalog
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()
    db.close.assert_called_once_with()


def test_commit_uses_approved_catalog_and_persists(monkeypatch):
    db = MagicMock()
    approved_catalog = _catalog()
    observed = {}

    monkeypatch.setattr(command, "SessionLocal", lambda: db)
    monkeypatch.setattr(command, "APPROVED_PRICING_CATALOG", approved_catalog)

    def fake_sync(session, prices):
        observed["session"] = session
        observed["prices"] = prices
        return _result()

    monkeypatch.setattr(command, "sync_pricing_catalog", fake_sync)

    result = command.run(commit=True)

    assert result == _result()
    assert observed["session"] is db
    assert observed["prices"] is approved_catalog
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()
    db.close.assert_called_once_with()


def test_failure_rolls_back_and_closes(monkeypatch):
    db = MagicMock()

    monkeypatch.setattr(command, "SessionLocal", lambda: db)
    monkeypatch.setattr(command, "APPROVED_PRICING_CATALOG", _catalog())

    def fail(_db, _prices):
        raise RuntimeError("pricing sync failed")

    monkeypatch.setattr(command, "sync_pricing_catalog", fail)

    with pytest.raises(RuntimeError, match="pricing sync failed"):
        command.run(commit=True)

    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()
    db.close.assert_called_once_with()


def test_result_output_is_explicit(capsys):
    command.print_result(_result())

    output = capsys.readouterr().out

    assert "prices_created=4" in output
    assert "prices_transitioned=2" in output
    assert "prices_unchanged=3" in output


def test_current_production_catalog_contains_no_unapproved_prices():
    # Intentional safety guard until launch pricing is formally approved.
    assert command.APPROVED_PRICING_CATALOG == ()
