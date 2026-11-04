from unittest.mock import MagicMock

import pytest

from api.services.product_catalog_sync import ProductCatalogSyncResult
from scripts import sync_product_catalog as command


def _result():
    return ProductCatalogSyncResult(
        plans_created=3,
        plans_updated=1,
        plans_unchanged=2,
        entitlements_created=10,
        entitlements_updated=4,
        entitlements_deleted=1,
    )


def test_parser_defaults_to_dry_run():
    args = command.build_parser().parse_args([])

    assert args.commit is False


def test_parser_accepts_explicit_commit():
    args = command.build_parser().parse_args(["--commit"])

    assert args.commit is True


def test_dry_run_rolls_back_and_does_not_commit(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(command, "SessionLocal", lambda: db)
    monkeypatch.setattr(command, "sync_product_catalog", lambda session: _result())

    result = command.run(commit=False)

    assert result == _result()
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()
    db.close.assert_called_once_with()


def test_commit_persists_transaction(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(command, "SessionLocal", lambda: db)
    monkeypatch.setattr(command, "sync_product_catalog", lambda session: _result())

    result = command.run(commit=True)

    assert result == _result()
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()
    db.close.assert_called_once_with()


def test_failure_rolls_back_and_closes(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(command, "SessionLocal", lambda: db)

    def fail(_db):
        raise RuntimeError("catalog sync failed")

    monkeypatch.setattr(command, "sync_product_catalog", fail)

    with pytest.raises(RuntimeError, match="catalog sync failed"):
        command.run(commit=True)

    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()
    db.close.assert_called_once_with()


def test_result_output_is_explicit(capsys):
    command.print_result(_result())

    output = capsys.readouterr().out

    assert "plans_created=3" in output
    assert "plans_updated=1" in output
    assert "plans_unchanged=2" in output
    assert "entitlements_created=10" in output
    assert "entitlements_updated=4" in output
    assert "entitlements_deleted=1" in output
