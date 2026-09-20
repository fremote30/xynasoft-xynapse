"""
XynaFaith V2 baseline product access policy.

Free Member and Free Pastor are role-aware baseline access profiles,
not subscription plans.

A paid subscription can augment or replace parts of this baseline
through the effective entitlement service.
"""

from dataclasses import dataclass
from typing import Optional

from api.core.access_profiles import (
    ACCESS_PROFILE_FREE_MEMBER,
    ACCESS_PROFILE_FREE_PASTOR,
)
from api.core.entitlements import (
    ENTITLEMENT_BIBLICAL_RESEARCH,
    ENTITLEMENT_BIBLE_STUDY_STUDIO,
    ENTITLEMENT_CONTENT_ENGINE,
    ENTITLEMENT_DEVOTIONAL_STUDIO,
    ENTITLEMENT_MEMBER_SERMON_NOTES,
    ENTITLEMENT_MULTILINGUAL,
    ENTITLEMENT_PASTOR_NETWORK,
    ENTITLEMENT_PRAYER_WALL,
    ENTITLEMENT_READING_PLANS,
    ENTITLEMENT_SERMON_SERIES,
    ENTITLEMENT_SERMON_STUDIO,
    ENTITLEMENT_SHARING,
    ENTITLEMENT_TESTIMONY_WALL,
    ENTITLEMENT_UNIVERSAL_SEARCH,
    ENTITLEMENT_XYNIVA_ACTIONS,
    ENTITLEMENT_XYNIVA_CHAT,
    ENTITLEMENT_XYNIVA_MEMORY,
)


@dataclass(frozen=True)
class AccessGrant:
    """
    One baseline entitlement.

    usage_limit=None means the entitlement is not numerically limited
    by this policy entry.

    usage_period is currently expected to be:
      - monthly
      - daily
      - None
    """

    entitlement_key: str
    enabled: bool = True
    usage_limit: Optional[int] = None
    usage_period: Optional[str] = None


# ============================================================
# FREE MEMBER
# ============================================================

FREE_MEMBER_GRANTS = (
    AccessGrant(
        ENTITLEMENT_XYNIVA_CHAT,
        usage_limit=30,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_XYNIVA_MEMORY,
    ),
    AccessGrant(
        ENTITLEMENT_XYNIVA_ACTIONS,
        usage_limit=10,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_PRAYER_WALL,
    ),
    AccessGrant(
        ENTITLEMENT_TESTIMONY_WALL,
    ),
    AccessGrant(
        ENTITLEMENT_READING_PLANS,
    ),
    AccessGrant(
        ENTITLEMENT_MEMBER_SERMON_NOTES,
    ),
    AccessGrant(
        ENTITLEMENT_SHARING,
    ),
    AccessGrant(
        ENTITLEMENT_UNIVERSAL_SEARCH,
    ),
    AccessGrant(
        ENTITLEMENT_MULTILINGUAL,
    ),
)


# ============================================================
# FREE PASTOR
# ============================================================

FREE_PASTOR_GRANTS = tuple(
    grant
    for grant in FREE_MEMBER_GRANTS
    if grant.entitlement_key not in {
        ENTITLEMENT_XYNIVA_CHAT,
        ENTITLEMENT_XYNIVA_ACTIONS,
    }
) + (
    # Pastors receive a meaningfully larger free Xyniva allowance.
    AccessGrant(
        ENTITLEMENT_XYNIVA_CHAT,
        usage_limit=75,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_XYNIVA_ACTIONS,
        usage_limit=25,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_SERMON_STUDIO,
        usage_limit=5,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_BIBLICAL_RESEARCH,
        usage_limit=5,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_CONTENT_ENGINE,
        usage_limit=5,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_SERMON_SERIES,
        usage_limit=2,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_DEVOTIONAL_STUDIO,
        usage_limit=5,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_BIBLE_STUDY_STUDIO,
        usage_limit=3,
        usage_period="monthly",
    ),
    AccessGrant(
        ENTITLEMENT_PASTOR_NETWORK,
    ),
)


PROFILE_GRANTS = {
    ACCESS_PROFILE_FREE_MEMBER: FREE_MEMBER_GRANTS,
    ACCESS_PROFILE_FREE_PASTOR: FREE_PASTOR_GRANTS,
}


def baseline_profile_for_role(role: str | None) -> str:
    """
    Resolve V1-compatible global identity role to a free product profile.

    This function does not grant Church Space authorization.
    Church authorization remains membership/RBAC based.
    """

    normalized = (role or "").strip().lower()

    if normalized == "pastor":
        return ACCESS_PROFILE_FREE_PASTOR

    return ACCESS_PROFILE_FREE_MEMBER


def baseline_grants(profile: str) -> tuple[AccessGrant, ...]:
    """
    Return baseline grants for a known free profile.

    Unknown profiles fail closed.
    """

    return PROFILE_GRANTS.get(profile, ())
