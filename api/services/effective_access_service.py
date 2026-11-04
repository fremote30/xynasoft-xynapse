"""
XynaFaith V2 Effective Access Service.

Public application-facing access API.

Application routes and product features should ask this service about
capabilities rather than inspect plans, subscriptions, or payment state.

The authoritative entitlement composition engine lives in:

    api.services.entitlement_service

That engine owns:

- role-aware free baseline access
- active individual subscriptions
- active Church subscriptions
- Church membership validation
- inactive/expired subscription handling
- entitlement merge semantics
- entitlement provenance

This module adapts that richer internal result into the stable
application-facing EffectiveAccessResponse and FeatureGateResponse.
"""

from typing import Optional

from sqlalchemy.orm import Session

from api.models.plan import Plan
from api.models.subscription import Subscription
from api.schemas.access import (
    EffectiveAccessResponse,
    FeatureGateResponse,
)
from api.services.entitlement_service import (
    EffectiveAccess,
    resolve_effective_access,
)


def _resolve_plan_code(
    db: Optional[Session],
    access: EffectiveAccess,
) -> Optional[str]:
    """
    Resolve the commercial plan code that contributed to effective access.

    Individual subscription takes precedence for the application-facing
    plan_code. If there is no individual subscription, an authorized Church
    subscription may supply the plan code.

    The entitlement engine remains authoritative for actual capabilities.
    """

    if db is None:
        return None

    subscription_id = (
        access.user_subscription_id
        or access.church_subscription_id
    )

    if subscription_id is None:
        return None

    row = (
        db.query(Subscription, Plan)
        .join(
            Plan,
            Plan.id == Subscription.plan_id,
        )
        .filter(
            Subscription.id == subscription_id,
        )
        .first()
    )

    if row is None:
        return None

    _subscription, plan = row

    return plan.code


def _resolve_access_profile(
    db: Optional[Session],
    access: EffectiveAccess,
) -> str:
    """
    Resolve the final presentation/access profile.

    baseline_profile records where free access originated.

    access_profile may expand to the active paid plan profile.

    If both individual and Church subscriptions are present, individual
    subscription profile takes precedence for this single display field.
    Effective entitlements themselves are still merged by the authoritative
    entitlement service.
    """

    if db is None:
        return access.baseline_profile

    subscription_id = (
        access.user_subscription_id
        or access.church_subscription_id
    )

    if subscription_id is None:
        return access.baseline_profile

    row = (
        db.query(Subscription, Plan)
        .join(
            Plan,
            Plan.id == Subscription.plan_id,
        )
        .filter(
            Subscription.id == subscription_id,
        )
        .first()
    )

    if row is None:
        return access.baseline_profile

    _subscription, plan = row

    return (
        plan.access_profile
        or access.baseline_profile
    )


def get_effective_access(
    db: Optional[Session],
    user,
    *,
    church_id: Optional[int] = None,
) -> EffectiveAccessResponse:
    """
    Return application-facing effective access for an authenticated user.

    Church-paid capabilities are considered only when church_id is explicitly
    supplied and the entitlement engine verifies an active membership.
    """

    if db is None:
        # The entitlement resolver expects a database session for paid access,
        # but baseline-only unit tests intentionally call this service without
        # one. Preserve that lightweight contract without duplicating paid
        # subscription logic.
        from api.core.access_policy import (
            baseline_grants,
            baseline_profile_for_role,
        )

        baseline_profile = baseline_profile_for_role(
            getattr(user, "role", None)
        )

        grants = {
            grant.entitlement_key: grant
            for grant in baseline_grants(baseline_profile)
            if grant.enabled
        }

        return EffectiveAccessResponse(
            user_id=user.id,
            role=getattr(user, "role", "member"),
            access_profile=baseline_profile,
            source_profile=baseline_profile,
            plan_code=None,
            entitlements=sorted(grants.keys()),
            limits={
                key: grant.usage_limit
                for key, grant in grants.items()
                if grant.usage_limit is not None
            },
        )

    resolved = resolve_effective_access(
        db,
        user=user,
        church_id=church_id,
    )

    access_profile = _resolve_access_profile(
        db,
        resolved,
    )

    plan_code = _resolve_plan_code(
        db,
        resolved,
    )

    enabled_entitlements = {
        key: grant
        for key, grant in resolved.entitlements.items()
        if grant.enabled
    }

    return EffectiveAccessResponse(
        user_id=user.id,
        role=getattr(user, "role", "member"),
        access_profile=access_profile,
        source_profile=resolved.baseline_profile,
        plan_code=plan_code,
        entitlements=sorted(
            enabled_entitlements.keys()
        ),
        limits={
            key: grant.usage_limit
            for key, grant in enabled_entitlements.items()
            if grant.usage_limit is not None
        },
    )


def has_entitlement(
    db: Optional[Session],
    user,
    entitlement_key: str,
    *,
    church_id: Optional[int] = None,
) -> bool:
    """
    Return whether the user has the requested effective entitlement.
    """

    access = get_effective_access(
        db,
        user,
        church_id=church_id,
    )

    return entitlement_key in access.entitlements


def check_feature_gate(
    db: Optional[Session],
    user,
    entitlement_key: str,
    *,
    church_id: Optional[int] = None,
) -> FeatureGateResponse:
    """
    Return a stable feature-gate decision for application code.
    """

    access = get_effective_access(
        db,
        user,
        church_id=church_id,
    )

    allowed = entitlement_key in access.entitlements

    return FeatureGateResponse(
        allowed=allowed,
        entitlement_key=entitlement_key,
        reason=(
            "entitlement_granted"
            if allowed
            else "missing_entitlement"
        ),
        access_profile=access.access_profile,
        plan_code=access.plan_code,
    )
