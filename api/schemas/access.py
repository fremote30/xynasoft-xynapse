"""
XynaFaith V2 effective access contracts.

These schemas represent resolved product access after evaluating:

- user role
- baseline access profile
- subscriptions
- plans
- entitlements
- usage limits

They are intentionally independent from payment providers.
"""

from typing import Optional

from pydantic import BaseModel, Field


class EntitlementAccess(BaseModel):
    """
    One resolved feature entitlement.
    """

    entitlement_key: str

    allowed: bool

    source: str = Field(
        description=(
            "Where access came from: "
            "free_profile, subscription, override"
        )
    )

    plan_code: Optional[str] = None

    reason: Optional[str] = None


class UsageAccess(BaseModel):
    """
    AI/product usage availability.
    """

    entitlement_key: str

    metric: str

    allowed: bool

    allowance_units: Optional[int] = None

    consumed_units: int = 0

    reserved_units: int = 0

    remaining_units: Optional[int] = None

    reason: Optional[str] = None


class AccessDecision(BaseModel):
    """
    Final decision returned by access checks.
    """

    allowed: bool

    entitlement_key: str

    source: Optional[str] = None

    reason: Optional[str] = None

    usage: Optional[UsageAccess] = None


class EffectiveAccessContext(BaseModel):
    """
    Complete resolved access state for a user.

    This becomes the object XynaFaith/Xyniva uses
    to decide what the user can do.
    """

    user_id: int

    role: str

    access_profile: str

    active_plan: Optional[str] = None

    entitlements: list[EntitlementAccess] = []

