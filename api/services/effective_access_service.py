"""
XynaFaith V2 Effective Access Engine.

Single authority for resolving:

- free member access
- pastor access
- paid subscriptions
- plan capabilities

Consumers should ask:

    has_entitlement(
        user,
        "xyniva.chat"
    )

not:

    if subscription.plan == pastor_pro

"""


from typing import Optional

from sqlalchemy.orm import Session

from api.schemas.access import (
    EffectiveAccessResponse,
)

from api.core.access_policy import (
    baseline_grants,
    baseline_profile_for_role,
)


def _safe_role(user):
    return getattr(
        user,
        "role",
        "member",
    )


def _subscription_for_user(
    db: Session,
    user_id: int,
):
    """
    Resolve active subscription.

    Defensive because subscription
    schema may evolve during V2.
    """

    try:
        from api.models.subscription import (
            Subscription,
        )

        return (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id
            )
            .filter(
                Subscription.status.in_(
                    [
                        "active",
                        "trialing",
                    ]
                )
            )
            .first()
        )

    except Exception:
        return None


def _plan_code(subscription):

    if not subscription:
        return None

    plan = getattr(
        subscription,
        "plan",
        None,
    )

    if not plan:
        return None

    return getattr(
        plan,
        "code",
        None,
    )


def _subscription_entitlements(
    subscription,
):

    if not subscription:
        return []

    plan = getattr(
        subscription,
        "plan",
        None,
    )

    if not plan:
        return []

    result = []

    entitlements = getattr(
        plan,
        "entitlements",
        [],
    )

    for item in entitlements:

        key = getattr(
            item,
            "key",
            None,
        )

        if key:
            result.append(key)

    return result


def get_effective_access(
    db: Session,
    *,
    user,
) -> EffectiveAccessResponse:
    """
    Resolve final user capability.
    """

    role = _safe_role(user)

    profile = baseline_profile_for_role(
        role
    )

    grants = set(
        baseline_grants(role)
    )

    subscription = _subscription_for_user(
        db,
        user.id,
    )


    subscription_grants = (
        _subscription_entitlements(
            subscription
        )
    )

    grants.update(
        subscription_grants
    )


    plan_code = _plan_code(
        subscription
    )


    return EffectiveAccessResponse(

        user_id=user.id,

        role=role,

        access_profile=(
            plan_code
            or profile
        ),

        plan_code=plan_code,

        entitlements=sorted(
            grants
        ),

        limits={},

        source_profile=(
            "subscription"
            if subscription
            else "baseline"
        ),
    )


def has_entitlement(
    db: Session,
    *,
    user,
    entitlement_key: str,
) -> bool:
    """
    Capability check.

    Example:

        has_entitlement(
            user,
            "xyniva.chat"
        )

    """

    access = get_effective_access(
        db,
        user=user,
    )

    return entitlement_key in (
        access.entitlements
    )
