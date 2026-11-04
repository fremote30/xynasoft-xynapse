"""
Synchronize the XynaFaith commercial product catalog with the configured database.

Safety:
- dry-run by default
- --commit is required to persist changes
- transaction is rolled back on dry-run
- transaction is rolled back on any error
- subscription state is not managed by this command

Examples:

    python scripts/sync_product_catalog.py

    python scripts/sync_product_catalog.py --commit
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from api.db.database import SessionLocal
from api.services.product_catalog_sync import (
    ProductCatalogSyncResult,
    sync_product_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize the XynaFaith commercial product catalog. "
            "Runs as a dry-run unless --commit is supplied."
        )
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist catalog synchronization changes.",
    )
    return parser


def print_result(result: ProductCatalogSyncResult) -> None:
    print("Catalog synchronization result:")
    print(f"  plans_created={result.plans_created}")
    print(f"  plans_updated={result.plans_updated}")
    print(f"  plans_unchanged={result.plans_unchanged}")
    print(f"  entitlements_created={result.entitlements_created}")
    print(f"  entitlements_updated={result.entitlements_updated}")
    print(f"  entitlements_deleted={result.entitlements_deleted}")


def run(*, commit: bool) -> ProductCatalogSyncResult:
    db = SessionLocal()

    try:
        result = sync_product_catalog(db)
        print_result(result)

        if commit:
            db.commit()
            print("Catalog synchronization committed.")
        else:
            db.rollback()
            print("Dry run complete. No catalog changes were written.")

        return result

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def main() -> None:
    args = build_parser().parse_args()

    print("XynaFaith Commercial Product Catalog")
    print("MODE:", "COMMIT" if args.commit else "DRY RUN")

    run(commit=args.commit)


if __name__ == "__main__":
    main()
