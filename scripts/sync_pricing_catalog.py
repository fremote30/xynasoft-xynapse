"""
Synchronize the approved XynaFaith pricing catalog with the configured database.

Safety:
- dry-run by default
- --commit is required to persist changes
- transaction is rolled back on dry-run
- transaction is rolled back on any error
- prices come only from the approved pricing catalog
- subscription and payment-provider state are not managed by this command
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from api.core.pricing_catalog import APPROVED_PRICING_CATALOG
from api.db.database import SessionLocal
from api.services.pricing_catalog_sync import (
    PricingCatalogSyncResult,
    sync_pricing_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize the approved XynaFaith commercial pricing catalog. "
            "Runs as a dry-run unless --commit is supplied."
        )
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist pricing synchronization changes.",
    )
    return parser


def print_result(result: PricingCatalogSyncResult) -> None:
    print("Pricing catalog synchronization result:")
    print(f"  prices_created={result.prices_created}")
    print(f"  prices_transitioned={result.prices_transitioned}")
    print(f"  prices_unchanged={result.prices_unchanged}")


def run(*, commit: bool) -> PricingCatalogSyncResult:
    db = SessionLocal()

    try:
        result = sync_pricing_catalog(
            db,
            APPROVED_PRICING_CATALOG,
        )
        print_result(result)

        if commit:
            db.commit()
            print("Pricing catalog synchronization committed.")
        else:
            db.rollback()
            print("Dry run complete. No pricing changes were written.")

        return result

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def main() -> None:
    args = build_parser().parse_args()

    print("XynaFaith Commercial Pricing Catalog")
    print("MODE:", "COMMIT" if args.commit else "DRY RUN")
    print(f"APPROVED PRICE ENTRIES: {len(APPROVED_PRICING_CATALOG)}")

    run(commit=args.commit)


if __name__ == "__main__":
    main()
