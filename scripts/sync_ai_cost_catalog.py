#!/usr/bin/env python3
"""Synchronize the reviewed XynAssist AI cost catalog."""

from __future__ import annotations

import argparse

from xynassist_service.core.ai_cost_catalog import (
    APPROVED_AI_COST_CATALOG,
)
from xynassist_service.database import SessionLocal
from xynassist_service.services.ai_cost_catalog_sync import (
    sync_ai_cost_catalog,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes. Default is dry-run.",
    )
    args = parser.parse_args()

    db = SessionLocal()

    try:
        result = sync_ai_cost_catalog(
            db,
            catalog=APPROVED_AI_COST_CATALOG,
        )

        print(result)

        if args.commit:
            db.commit()
            print("AI cost catalog sync committed.")
        else:
            db.rollback()
            print("Dry run complete; no changes persisted.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
