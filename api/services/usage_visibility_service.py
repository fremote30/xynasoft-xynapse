"""
Read-only XynaFaith V2 usage/quota visibility.

This service exposes the current authoritative metering state without
creating or mutating UsageBucket rows.

Quota ownership follows the effective entitlement that won composition:
- baseline or user subscription -> user quota bucket
- church subscription -> church quota bucket
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.models.subscription import Subscription
from api.models.usage_bucket import UsageBucket
from api.services.ai_usage_metering import UsagePeriod, resolve_usage_period
from api.services.entitlement_service import (
    EffectiveEntitlement,
    resolve_effective_access,
)


class UsageVisibilityDenied(Exception):
    """The requested metered entitlement is unavailable."""


class UsageVisibilityConfigurationError(Exception):
    """The effective entitlement cannot safely expose quota state."""


@dataclass(frozen=True)
class UsageVisibility:
    entitlement_key: str
    metric: str
    quota_owner_type: str
    quota_owner_id: int
    allowance_units: int
    consumed_units: int
    reserved_units: int
    available_units: int
    period_start: datetime
    period_end: datetime
    source: str


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
        raise UsageVisibilityConfigurationError(
            f"Invalid entitlement source: {grant.source}"
        ) from exc


def _resolve_period(
    db: Session,
    *,
    grant: EffectiveEntitlement,
    now: Optional[datetime],
) -> UsagePeriod:
    subscription_id = _subscription_id_from_source(grant)

    if subscription_id is None:
        return resolve_usage_period(
            grant.usage_period,
            now=now,
        )

    subscription = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id)
        .one_or_none()
    )

    if subscription is None:
        raise UsageVisibilityConfigurationError(
            "Entitlement references a missing subscription"
        )

    period_start = subscription.current_period_start
    period_end = subscription.current_period_end

    if period_start is None and period_end is None:
        return resolve_usage_period(
            grant.usage_period,
            now=now,
        )

    if period_start is None or period_end is None:
        raise UsageVisibilityConfigurationError(
            "Subscription has an incomplete billing period"
        )

    if period_start >= period_end:
        raise UsageVisibilityConfigurationError(
            "Subscription has an invalid billing period"
        )

    return UsagePeriod(
        start=period_start,
        end=period_end,
    )


def get_usage_visibility(
    db: Session,
    *,
    user,
    entitlement_key: str,
    metric: str,
    church_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> UsageVisibility:
    """
    Return current quota visibility without creating a UsageBucket.
    """

    access = resolve_effective_access(
        db,
        user=user,
        church_id=church_id,
        now=now,
    )

    grant = access.get(entitlement_key)

    if grant is None or not grant.enabled:
        raise UsageVisibilityDenied(
            f"Missing entitlement: {entitlement_key}"
        )

    if grant.usage_limit is None:
        raise UsageVisibilityConfigurationError(
            f"{entitlement_key} is unlimited and has no numeric quota"
        )

    if not grant.usage_period:
        raise UsageVisibilityConfigurationError(
            f"{entitlement_key} has a finite limit but no usage period"
        )

    period = _resolve_period(
        db,
        grant=grant,
        now=now,
    )

    if grant.source.startswith("church_subscription:"):
        if church_id is None:
            raise UsageVisibilityConfigurationError(
                "Church entitlement resolved without Church context"
            )

        quota_owner_type = "church"
        quota_owner_id = church_id

        query = db.query(UsageBucket).filter(
            UsageBucket.user_id.is_(None),
            UsageBucket.church_id == church_id,
        )
    else:
        quota_owner_type = "user"
        quota_owner_id = user.id

        query = db.query(UsageBucket).filter(
            UsageBucket.user_id == user.id,
            UsageBucket.church_id.is_(None),
        )

    bucket = (
        query.filter(
            UsageBucket.entitlement_key == entitlement_key,
            UsageBucket.metric == metric,
            UsageBucket.period_start == period.start,
        )
        .one_or_none()
    )

    if bucket is None:
        allowance_units = grant.usage_limit
        consumed_units = 0
        reserved_units = 0
        period_start = period.start
        period_end = period.end
    else:
        # The persisted bucket is authoritative once metering has begun.
        allowance_units = bucket.allowance_units
        consumed_units = bucket.consumed_units
        reserved_units = bucket.reserved_units
        period_start = bucket.period_start
        period_end = bucket.period_end

    available_units = max(
        allowance_units - consumed_units - reserved_units,
        0,
    )

    return UsageVisibility(
        entitlement_key=entitlement_key,
        metric=metric,
        quota_owner_type=quota_owner_type,
        quota_owner_id=quota_owner_id,
        allowance_units=allowance_units,
        consumed_units=consumed_units,
        reserved_units=reserved_units,
        available_units=available_units,
        period_start=period_start,
        period_end=period_end,
        source=grant.source,
    )
