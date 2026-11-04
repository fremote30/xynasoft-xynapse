"""
XynaFaith V2 effective entitlement resolution.

Access is composed from:

1. role-aware free baseline
2. active individual subscription
3. active Church subscription, but only in an authorized Church context

Routes should ask this service about capabilities rather than inspect
plan names directly.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.core.access_policy import (
    AccessGrant,
    baseline_grants,
    baseline_profile_for_role,
)
from api.models.church_membership import ChurchMembership
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription


ACTIVE_SUBSCRIPTION_STATUSES = frozenset(
    {
        "active",
        "trialing",
    }
)

ACTIVE_MEMBERSHIP_STATUS = "active"


@dataclass(frozen=True)
class EffectiveEntitlement:
    entitlement_key: str
    enabled: bool
    usage_limit: Optional[int]
    usage_period: Optional[str]
    source: str


@dataclass(frozen=True)
class EffectiveAccess:
    baseline_profile: str
    entitlements: dict[str, EffectiveEntitlement]
    user_subscription_id: Optional[int] = None
    church_subscription_id: Optional[int] = None
    church_id: Optional[int] = None

    def has(self, entitlement_key: str) -> bool:
        grant = self.entitlements.get(entitlement_key)
        return bool(grant and grant.enabled)

    def get(
        self,
        entitlement_key: str,
    ) -> Optional[EffectiveEntitlement]:
        return self.entitlements.get(entitlement_key)


def _subscription_is_current(
    subscription: Subscription,
    now: datetime,
) -> bool:
    if subscription.status not in ACTIVE_SUBSCRIPTION_STATUSES:
        return False

    if subscription.starts_at and subscription.starts_at > now:
        return False

    if (
        subscription.current_period_end is not None
        and subscription.current_period_end <= now
    ):
        return False

    return True


def _merge_grant(
    target: dict[str, EffectiveEntitlement],
    incoming: EffectiveEntitlement,
) -> None:
    """
    Merge one enabled entitlement into effective access.

    Rules:
    - disabled grants do not revoke an existing baseline capability
    - unlimited (None) beats a numeric limit
    - otherwise the larger numeric allowance wins
    """

    if not incoming.enabled:
        return

    existing = target.get(incoming.entitlement_key)

    if existing is None:
        target[incoming.entitlement_key] = incoming
        return

    if existing.usage_limit is None:
        return

    if incoming.usage_limit is None:
        target[incoming.entitlement_key] = incoming
        return

    if incoming.usage_limit > existing.usage_limit:
        target[incoming.entitlement_key] = incoming


def _baseline_entitlements(
    role: str | None,
) -> tuple[str, dict[str, EffectiveEntitlement]]:
    profile = baseline_profile_for_role(role)

    grants: dict[str, EffectiveEntitlement] = {}

    for grant in baseline_grants(profile):
        _merge_grant(
            grants,
            EffectiveEntitlement(
                entitlement_key=grant.entitlement_key,
                enabled=grant.enabled,
                usage_limit=grant.usage_limit,
                usage_period=grant.usage_period,
                source=f"baseline:{profile}",
            ),
        )

    return profile, grants


def _load_plan_entitlements(
    db: Session,
    plan_id: int,
    *,
    source: str,
) -> list[EffectiveEntitlement]:
    rows = (
        db.query(PlanEntitlement)
        .filter(PlanEntitlement.plan_id == plan_id)
        .all()
    )

    return [
        EffectiveEntitlement(
            entitlement_key=row.entitlement_key,
            enabled=row.enabled,
            usage_limit=row.usage_limit,
            usage_period=row.usage_period,
            source=source,
        )
        for row in rows
    ]


def _find_current_user_subscription(
    db: Session,
    user_id: int,
    now: datetime,
) -> Optional[Subscription]:
    subscriptions = (
        db.query(Subscription)
        .join(Plan, Plan.id == Subscription.plan_id)
        .filter(
            Subscription.user_id == user_id,
            Subscription.church_id.is_(None),
            Plan.is_active.is_(True),
        )
        .order_by(
            Subscription.created_at.desc(),
            Subscription.id.desc(),
        )
        .all()
    )

    for subscription in subscriptions:
        if _subscription_is_current(subscription, now):
            return subscription

    return None


def _find_current_church_subscription(
    db: Session,
    church_id: int,
    now: datetime,
) -> Optional[Subscription]:
    subscriptions = (
        db.query(Subscription)
        .join(Plan, Plan.id == Subscription.plan_id)
        .filter(
            Subscription.church_id == church_id,
            Subscription.user_id.is_(None),
            Plan.is_active.is_(True),
        )
        .order_by(
            Subscription.created_at.desc(),
            Subscription.id.desc(),
        )
        .all()
    )

    for subscription in subscriptions:
        if _subscription_is_current(subscription, now):
            return subscription

    return None


def _has_active_church_membership(
    db: Session,
    *,
    user_id: int,
    church_id: int,
) -> bool:
    membership = (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.user_id == user_id,
            ChurchMembership.church_id == church_id,
            ChurchMembership.status == ACTIVE_MEMBERSHIP_STATUS,
        )
        .first()
    )

    return membership is not None


def resolve_effective_access(
    db: Session,
    *,
    user,
    church_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> EffectiveAccess:
    """
    Resolve effective product access for an authenticated user.

    Church-paid entitlements are inherited only when:
    - church_id is explicitly supplied, and
    - the authenticated user has an active membership in that church.
    """

    now = now or datetime.utcnow()

    profile, entitlements = _baseline_entitlements(
        getattr(user, "role", None)
    )

    user_subscription = _find_current_user_subscription(
        db,
        user_id=user.id,
        now=now,
    )

    if user_subscription is not None:
        for entitlement in _load_plan_entitlements(
            db,
            user_subscription.plan_id,
            source=f"user_subscription:{user_subscription.id}",
        ):
            _merge_grant(entitlements, entitlement)

    church_subscription = None

    if church_id is not None and _has_active_church_membership(
        db,
        user_id=user.id,
        church_id=church_id,
    ):
        church_subscription = _find_current_church_subscription(
            db,
            church_id=church_id,
            now=now,
        )

        if church_subscription is not None:
            for entitlement in _load_plan_entitlements(
                db,
                church_subscription.plan_id,
                source=f"church_subscription:{church_subscription.id}",
            ):
                _merge_grant(entitlements, entitlement)

    return EffectiveAccess(
        baseline_profile=profile,
        entitlements=entitlements,
        user_subscription_id=(
            user_subscription.id
            if user_subscription is not None
            else None
        ),
        church_subscription_id=(
            church_subscription.id
            if church_subscription is not None
            else None
        ),
        church_id=church_id,
    )
