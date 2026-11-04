"""
Synchronize the static XynaFaith commercial product catalog into the database.

The static product catalog is authoritative for the commercial Plan rows it
owns and for their PlanEntitlement rows.

This service deliberately:
- does not commit transactions
- does not create or modify subscriptions
- does not delete Plan rows
- does not deactivate unrelated/unknown Plan rows
- preserves existing Plan primary keys
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from api.core.product_catalog import (
    COMMERCIAL_PLANS,
    CatalogPlan,
    validate_product_catalog,
)
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement


@dataclass(frozen=True)
class ProductCatalogSyncResult:
    plans_created: int = 0
    plans_updated: int = 0
    plans_unchanged: int = 0
    entitlements_created: int = 0
    entitlements_updated: int = 0
    entitlements_deleted: int = 0


def _sync_plan(
    db: Session,
    catalog_plan: CatalogPlan,
) -> tuple[int, int, int, int, int, int]:
    plan = (
        db.query(Plan)
        .filter(Plan.code == catalog_plan.code)
        .one_or_none()
    )

    plans_created = 0
    plans_updated = 0
    plans_unchanged = 0
    entitlements_created = 0
    entitlements_updated = 0
    entitlements_deleted = 0

    if plan is None:
        plan = Plan(
            code=catalog_plan.code,
            name=catalog_plan.name,
            access_profile=catalog_plan.access_profile,
            owner_type=catalog_plan.owner_type,
            is_active=True,
        )
        db.add(plan)
        db.flush()
        plans_created = 1
    else:
        changed = False

        desired_plan_values = {
            "name": catalog_plan.name,
            "access_profile": catalog_plan.access_profile,
            "owner_type": catalog_plan.owner_type,
            "is_active": True,
        }

        for field, desired_value in desired_plan_values.items():
            if getattr(plan, field) != desired_value:
                setattr(plan, field, desired_value)
                changed = True

        if changed:
            plans_updated = 1
        else:
            plans_unchanged = 1

    existing_by_key = {
        entitlement.entitlement_key: entitlement
        for entitlement in plan.entitlements
    }

    desired_by_key = {
        entitlement.entitlement_key: entitlement
        for entitlement in catalog_plan.entitlements
    }

    for entitlement_key, desired in desired_by_key.items():
        existing = existing_by_key.get(entitlement_key)

        if existing is None:
            db.add(
                PlanEntitlement(
                    plan_id=plan.id,
                    entitlement_key=desired.entitlement_key,
                    enabled=desired.enabled,
                    usage_limit=desired.usage_limit,
                    usage_period=desired.usage_period,
                )
            )
            entitlements_created += 1
            continue

        changed = False

        desired_values = {
            "enabled": desired.enabled,
            "usage_limit": desired.usage_limit,
            "usage_period": desired.usage_period,
        }

        for field, desired_value in desired_values.items():
            if getattr(existing, field) != desired_value:
                setattr(existing, field, desired_value)
                changed = True

        if changed:
            entitlements_updated += 1

    stale_keys = set(existing_by_key) - set(desired_by_key)

    for entitlement_key in stale_keys:
        db.delete(existing_by_key[entitlement_key])
        entitlements_deleted += 1

    db.flush()

    return (
        plans_created,
        plans_updated,
        plans_unchanged,
        entitlements_created,
        entitlements_updated,
        entitlements_deleted,
    )


def sync_product_catalog(db: Session) -> ProductCatalogSyncResult:
    """
    Reconcile catalog-owned Plan and PlanEntitlement rows.

    Transaction ownership belongs to the caller. This function flushes so
    callers can inspect synchronized rows immediately, but it never commits.
    """

    validate_product_catalog()

    totals = [0, 0, 0, 0, 0, 0]

    for catalog_plan in COMMERCIAL_PLANS:
        result = _sync_plan(db, catalog_plan)

        for index, value in enumerate(result):
            totals[index] += value

    return ProductCatalogSyncResult(
        plans_created=totals[0],
        plans_updated=totals[1],
        plans_unchanged=totals[2],
        entitlements_created=totals[3],
        entitlements_updated=totals[4],
        entitlements_deleted=totals[5],
    )
