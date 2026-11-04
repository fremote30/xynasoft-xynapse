"""
XynaFaith V2 Xyniva usage orchestration.

This service connects effective entitlement resolution to the existing
atomic AI usage metering engine.

It does not implement entitlement composition or low-level quota
accounting itself.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.services.ai_usage_metering import (
    UsagePeriod,
    complete_usage,
    release_usage,
    reserve_usage,
)
from api.services.entitlement_service import (
    EffectiveEntitlement,
    resolve_effective_access,
)
from api.models.subscription import Subscription


class XynivaUsageDenied(Exception):
    """The authenticated user does not have the requested capability."""


class XynivaUsageConfigurationError(Exception):
    """The effective entitlement cannot safely be metered."""


def _subscription_id_from_source(
    grant: EffectiveEntitlement,
) -> Optional[int]:
    prefix, separator, raw_id = grant.source.partition(":")

    if not separator:
        return None

    if prefix not in {
        "user_subscription",
        "church_subscription",
    }:
        return None

    try:
        return int(raw_id)
    except ValueError as exc:
        raise XynivaUsageConfigurationError(
            f"Invalid entitlement source: {grant.source}"
        ) from exc


def _load_subscription_period(
    db: Session,
    *,
    subscription_id: Optional[int],
) -> Optional[UsagePeriod]:
    if subscription_id is None:
        return None

    subscription = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id)
        .one_or_none()
    )

    if subscription is None:
        raise XynivaUsageConfigurationError(
            "Entitlement references a missing subscription"
        )

    period_start = subscription.current_period_start
    period_end = subscription.current_period_end

    if period_start is None and period_end is None:
        return None

    if period_start is None or period_end is None:
        raise XynivaUsageConfigurationError(
            "Subscription has an incomplete billing period"
        )

    if period_start >= period_end:
        raise XynivaUsageConfigurationError(
            "Subscription has an invalid billing period"
        )

    return UsagePeriod(
        start=period_start,
        end=period_end,
    )


def reserve_xyniva_usage(
    db: Session,
    *,
    user,
    request_id: str,
    entitlement_key: str = "xyniva.chat",
    metric: str = "xyniva_turn",
    units: int = 1,
    church_id: Optional[int] = None,
    now: Optional[datetime] = None,
):
    """
    Resolve effective access and reserve quota before expensive AI work.

    Quota ownership follows the entitlement that actually won composition:

    - baseline or user subscription -> user quota bucket
    - church subscription -> church quota bucket

    Unlimited entitlements are intentionally rejected here until an
    unmetered-but-audited execution path is implemented. A large numeric
    sentinel must not be used to represent unlimited access.
    """

    access = resolve_effective_access(
        db,
        user=user,
        church_id=church_id,
        now=now,
    )

    grant = access.get(entitlement_key)

    if grant is None or not grant.enabled:
        raise XynivaUsageDenied(
            f"Missing entitlement: {entitlement_key}"
        )

    if grant.usage_limit is None:
        raise XynivaUsageConfigurationError(
            f"{entitlement_key} is unlimited and requires "
            "the unmetered audit path"
        )

    if not grant.usage_period:
        raise XynivaUsageConfigurationError(
            f"{entitlement_key} has a finite limit but no usage period"
        )

    subscription_id = _subscription_id_from_source(grant)

    if grant.source.startswith("church_subscription:"):
        if church_id is None:
            raise XynivaUsageConfigurationError(
                "Church entitlement resolved without Church context"
            )

        quota_user_id = None
        quota_church_id = church_id

    else:
        quota_user_id = user.id
        quota_church_id = None

    explicit_period = _load_subscription_period(
        db,
        subscription_id=subscription_id,
    )

    return reserve_usage(
        db,
        request_id=request_id,
        actor_user_id=user.id,
        quota_user_id=quota_user_id,
        quota_church_id=quota_church_id,
        subscription_id=subscription_id,
        entitlement_key=entitlement_key,
        metric=metric,
        units=units,
        allowance_units=grant.usage_limit,
        usage_period=grant.usage_period,
        explicit_period=explicit_period,
        now=now,
    )


def complete_xyniva_usage(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
):
    """Consume a successful Xyniva usage reservation."""

    return complete_usage(
        db,
        request_id=request_id,
        now=now,
    )


def release_xyniva_usage(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
):
    """Release reserved quota after failed AI work."""

    return release_usage(
        db,
        request_id=request_id,
        now=now,
    )
