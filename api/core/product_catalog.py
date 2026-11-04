"""
XynaFaith V2 commercial product catalog.

This module defines what XynaFaith sells.

It intentionally contains:
- no payment-provider product IDs
- no prices or currencies
- no database writes
- no subscription state

Free Member and Free Pastor are role-aware baseline profiles and therefore
are not commercial Plan definitions.

Commercial plans grant capabilities through the shared entitlement
vocabulary. Payment systems may later map external products/prices onto
these stable internal plan codes.
"""

from dataclasses import dataclass
from typing import Optional

from api.core.access_profiles import (
    ACCESS_PROFILE_CHURCH,
    ACCESS_PROFILE_CHURCH_PRO,
    ACCESS_PROFILE_PASTOR_PRO,
    is_known_access_profile,
)
from api.core.entitlements import (
    ENTITLEMENT_ANNOUNCEMENTS,
    ENTITLEMENT_BIBLICAL_RESEARCH,
    ENTITLEMENT_BIBLE_STUDY_STUDIO,
    ENTITLEMENT_CHURCH_INTELLIGENCE,
    ENTITLEMENT_CHURCH_MEMBERS,
    ENTITLEMENT_CHURCH_GROUPS,
    ENTITLEMENT_CHURCH_SPACE,
    ENTITLEMENT_CONTENT_ENGINE,
    ENTITLEMENT_DEVOTIONAL_STUDIO,
    ENTITLEMENT_EVENTS,
    ENTITLEMENT_MEMBER_SERMON_NOTES,
    ENTITLEMENT_MINISTRY_BRIEF,
    ENTITLEMENT_MULTILINGUAL,
    ENTITLEMENT_PASTORAL_CARE,
    ENTITLEMENT_PASTOR_NETWORK,
    ENTITLEMENT_PRAYER_WALL,
    ENTITLEMENT_READING_PLANS,
    ENTITLEMENT_BIBLE_QUIZZES,
    ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    ENTITLEMENT_BIBLE_QUIZZES_AI,
    ENTITLEMENT_SERMON_SERIES,
    ENTITLEMENT_SERMON_STUDIO,
    ENTITLEMENT_SERMON_STUDIO_ADVANCED,
    ENTITLEMENT_SHARING,
    ENTITLEMENT_TESTIMONY_WALL,
    ENTITLEMENT_UNIVERSAL_SEARCH,
    ENTITLEMENT_XYNIVA_ACTIONS,
    ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS,
    ENTITLEMENT_XYNIVA_ADVANCED_MEMORY,
    ENTITLEMENT_XYNIVA_CHAT,
    ENTITLEMENT_XYNIVA_MEMORY,
    is_known_entitlement,
)


PLAN_CODE_PASTOR_PRO = "pastor_pro"
PLAN_CODE_CHURCH = "church"
PLAN_CODE_CHURCH_PRO = "church_pro"

OWNER_TYPE_INDIVIDUAL = "individual"
OWNER_TYPE_CHURCH = "church"

VALID_OWNER_TYPES = frozenset(
    {
        OWNER_TYPE_INDIVIDUAL,
        OWNER_TYPE_CHURCH,
    }
)

VALID_USAGE_PERIODS = frozenset(
    {
        "daily",
        "monthly",
    }
)


@dataclass(frozen=True)
class CatalogEntitlement:
    entitlement_key: str
    usage_limit: Optional[int] = None
    usage_period: Optional[str] = None
    enabled: bool = True


@dataclass(frozen=True)
class CatalogPlan:
    code: str
    name: str
    access_profile: str
    owner_type: str
    entitlements: tuple[CatalogEntitlement, ...]


def _grant(
    entitlement_key: str,
    *,
    usage_limit: Optional[int] = None,
    usage_period: Optional[str] = None,
) -> CatalogEntitlement:
    return CatalogEntitlement(
        entitlement_key=entitlement_key,
        usage_limit=usage_limit,
        usage_period=usage_period,
    )


PASTOR_PRO = CatalogPlan(
    code=PLAN_CODE_PASTOR_PRO,
    name="Pastor Pro",
    access_profile=ACCESS_PROFILE_PASTOR_PRO,
    owner_type=OWNER_TYPE_INDIVIDUAL,
    entitlements=(
        _grant(
            ENTITLEMENT_XYNIVA_CHAT,
            usage_limit=500,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_XYNIVA_MEMORY),
        _grant(ENTITLEMENT_XYNIVA_ADVANCED_MEMORY),
        _grant(
            ENTITLEMENT_XYNIVA_ACTIONS,
            usage_limit=150,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS),
        _grant(
            ENTITLEMENT_SERMON_STUDIO,
            usage_limit=50,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_SERMON_STUDIO_ADVANCED),
        _grant(
            ENTITLEMENT_BIBLICAL_RESEARCH,
            usage_limit=50,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_CONTENT_ENGINE,
            usage_limit=50,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_SERMON_SERIES,
            usage_limit=15,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_DEVOTIONAL_STUDIO,
            usage_limit=30,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_BIBLE_STUDY_STUDIO,
            usage_limit=20,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_PRAYER_WALL),
        _grant(ENTITLEMENT_TESTIMONY_WALL),
        _grant(ENTITLEMENT_READING_PLANS),
        _grant(ENTITLEMENT_MEMBER_SERMON_NOTES),
        _grant(ENTITLEMENT_SHARING),
        _grant(ENTITLEMENT_BIBLE_QUIZZES),
        _grant(ENTITLEMENT_BIBLE_QUIZZES_AUTHOR),
        _grant(
            ENTITLEMENT_BIBLE_QUIZZES_AI,
            usage_limit=100,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_PASTOR_NETWORK),
        _grant(ENTITLEMENT_UNIVERSAL_SEARCH),
        _grant(ENTITLEMENT_MULTILINGUAL),
    ),
)


CHURCH = CatalogPlan(
    code=PLAN_CODE_CHURCH,
    name="Church",
    access_profile=ACCESS_PROFILE_CHURCH,
    owner_type=OWNER_TYPE_CHURCH,
    entitlements=(
        _grant(
            ENTITLEMENT_XYNIVA_CHAT,
            usage_limit=1000,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_XYNIVA_MEMORY),
        _grant(
            ENTITLEMENT_XYNIVA_ACTIONS,
            usage_limit=250,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_SERMON_STUDIO,
            usage_limit=100,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_BIBLICAL_RESEARCH,
            usage_limit=100,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_CONTENT_ENGINE,
            usage_limit=100,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_SERMON_SERIES,
            usage_limit=25,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_DEVOTIONAL_STUDIO,
            usage_limit=50,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_BIBLE_STUDY_STUDIO,
            usage_limit=40,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_PRAYER_WALL),
        _grant(ENTITLEMENT_TESTIMONY_WALL),
        _grant(ENTITLEMENT_READING_PLANS),
        _grant(ENTITLEMENT_BIBLE_QUIZZES),
        _grant(ENTITLEMENT_BIBLE_QUIZZES_AUTHOR),
        _grant(ENTITLEMENT_MEMBER_SERMON_NOTES),
        _grant(ENTITLEMENT_SHARING),
        _grant(ENTITLEMENT_PASTOR_NETWORK),
        _grant(ENTITLEMENT_CHURCH_SPACE),
        _grant(ENTITLEMENT_CHURCH_MEMBERS),
        _grant(ENTITLEMENT_CHURCH_GROUPS),
        _grant(ENTITLEMENT_PASTORAL_CARE),
        _grant(ENTITLEMENT_ANNOUNCEMENTS),
        _grant(ENTITLEMENT_EVENTS),
        _grant(ENTITLEMENT_UNIVERSAL_SEARCH),
        _grant(ENTITLEMENT_MULTILINGUAL),
    ),
)


CHURCH_PRO = CatalogPlan(
    code=PLAN_CODE_CHURCH_PRO,
    name="Church Pro",
    access_profile=ACCESS_PROFILE_CHURCH_PRO,
    owner_type=OWNER_TYPE_CHURCH,
    entitlements=(
        _grant(
            ENTITLEMENT_XYNIVA_CHAT,
            usage_limit=5000,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_XYNIVA_MEMORY),
        _grant(ENTITLEMENT_XYNIVA_ADVANCED_MEMORY),
        _grant(
            ENTITLEMENT_XYNIVA_ACTIONS,
            usage_limit=1500,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS),
        _grant(
            ENTITLEMENT_SERMON_STUDIO,
            usage_limit=500,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_SERMON_STUDIO_ADVANCED),
        _grant(
            ENTITLEMENT_BIBLICAL_RESEARCH,
            usage_limit=500,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_CONTENT_ENGINE,
            usage_limit=500,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_SERMON_SERIES,
            usage_limit=100,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_DEVOTIONAL_STUDIO,
            usage_limit=250,
            usage_period="monthly",
        ),
        _grant(
            ENTITLEMENT_BIBLE_STUDY_STUDIO,
            usage_limit=200,
            usage_period="monthly",
        ),
        _grant(ENTITLEMENT_PRAYER_WALL),
        _grant(ENTITLEMENT_TESTIMONY_WALL),
        _grant(ENTITLEMENT_READING_PLANS),
        _grant(ENTITLEMENT_BIBLE_QUIZZES),
        _grant(ENTITLEMENT_BIBLE_QUIZZES_AUTHOR),
        _grant(ENTITLEMENT_BIBLE_QUIZZES_AI),
        _grant(ENTITLEMENT_MEMBER_SERMON_NOTES),
        _grant(ENTITLEMENT_SHARING),
        _grant(ENTITLEMENT_PASTOR_NETWORK),
        _grant(ENTITLEMENT_CHURCH_SPACE),
        _grant(ENTITLEMENT_CHURCH_MEMBERS),
        _grant(ENTITLEMENT_CHURCH_GROUPS),
        _grant(ENTITLEMENT_PASTORAL_CARE),
        _grant(ENTITLEMENT_ANNOUNCEMENTS),
        _grant(ENTITLEMENT_EVENTS),
        _grant(ENTITLEMENT_CHURCH_INTELLIGENCE),
        _grant(ENTITLEMENT_MINISTRY_BRIEF),
        _grant(ENTITLEMENT_UNIVERSAL_SEARCH),
        _grant(ENTITLEMENT_MULTILINGUAL),
    ),
)


COMMERCIAL_PLANS = (
    PASTOR_PRO,
    CHURCH,
    CHURCH_PRO,
)

COMMERCIAL_PLAN_BY_CODE = {
    plan.code: plan
    for plan in COMMERCIAL_PLANS
}


def get_commercial_plan(code: str) -> Optional[CatalogPlan]:
    return COMMERCIAL_PLAN_BY_CODE.get(code)


def validate_product_catalog() -> None:
    """
    Fail fast if the static commercial catalog violates product contracts.
    """

    codes = [plan.code for plan in COMMERCIAL_PLANS]

    if len(codes) != len(set(codes)):
        raise ValueError("Commercial plan codes must be unique")

    for plan in COMMERCIAL_PLANS:
        if not is_known_access_profile(plan.access_profile):
            raise ValueError(
                f"Unknown access profile for plan {plan.code}: "
                f"{plan.access_profile}"
            )

        if plan.owner_type not in VALID_OWNER_TYPES:
            raise ValueError(
                f"Invalid owner type for plan {plan.code}: "
                f"{plan.owner_type}"
            )

        entitlement_keys = [
            grant.entitlement_key
            for grant in plan.entitlements
        ]

        if len(entitlement_keys) != len(set(entitlement_keys)):
            raise ValueError(
                f"Duplicate entitlement in plan {plan.code}"
            )

        for grant in plan.entitlements:
            if not is_known_entitlement(grant.entitlement_key):
                raise ValueError(
                    f"Unknown entitlement in plan {plan.code}: "
                    f"{grant.entitlement_key}"
                )

            if grant.usage_limit is not None:
                if grant.usage_limit <= 0:
                    raise ValueError(
                        f"Usage limit must be positive for "
                        f"{plan.code}:{grant.entitlement_key}"
                    )

                if grant.usage_period not in VALID_USAGE_PERIODS:
                    raise ValueError(
                        f"Metered entitlement requires a valid period for "
                        f"{plan.code}:{grant.entitlement_key}"
                    )

            elif grant.usage_period is not None:
                raise ValueError(
                    f"Unmetered entitlement cannot declare a usage period for "
                    f"{plan.code}:{grant.entitlement_key}"
                )


validate_product_catalog()
