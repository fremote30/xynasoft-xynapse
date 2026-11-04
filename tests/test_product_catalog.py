"""
XynaFaith V2 commercial product catalog tests.
"""

from api.core.access_policy import (
    FREE_MEMBER_GRANTS,
    FREE_PASTOR_GRANTS,
)
from api.core.entitlements import (
    ENTITLEMENT_CHURCH_INTELLIGENCE,
    ENTITLEMENT_CHURCH_SPACE,
    ENTITLEMENT_MINISTRY_BRIEF,
    ENTITLEMENT_SERMON_STUDIO,
    ENTITLEMENT_SERMON_STUDIO_ADVANCED,
    ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS,
    ENTITLEMENT_XYNIVA_ADVANCED_MEMORY,
    ENTITLEMENT_XYNIVA_CHAT,
)
from api.core.product_catalog import (
    CHURCH,
    CHURCH_PRO,
    COMMERCIAL_PLANS,
    OWNER_TYPE_CHURCH,
    OWNER_TYPE_INDIVIDUAL,
    PASTOR_PRO,
    PLAN_CODE_CHURCH,
    PLAN_CODE_CHURCH_PRO,
    PLAN_CODE_PASTOR_PRO,
    get_commercial_plan,
    validate_product_catalog,
)


def _grant_map(plan):
    return {
        grant.entitlement_key: grant
        for grant in plan.entitlements
    }


def test_catalog_is_valid():
    validate_product_catalog()


def test_only_three_paid_launch_plans_exist():
    assert len(COMMERCIAL_PLANS) == 3

    assert {
        plan.code
        for plan in COMMERCIAL_PLANS
    } == {
        PLAN_CODE_PASTOR_PRO,
        PLAN_CODE_CHURCH,
        PLAN_CODE_CHURCH_PRO,
    }


def test_free_profiles_are_not_commercial_plans():
    commercial_codes = {
        plan.code
        for plan in COMMERCIAL_PLANS
    }

    assert "free_member" not in commercial_codes
    assert "free_pastor" not in commercial_codes

    assert FREE_MEMBER_GRANTS
    assert FREE_PASTOR_GRANTS


def test_plan_lookup_fails_closed():
    assert get_commercial_plan(PLAN_CODE_PASTOR_PRO) is PASTOR_PRO
    assert get_commercial_plan(PLAN_CODE_CHURCH) is CHURCH
    assert get_commercial_plan(PLAN_CODE_CHURCH_PRO) is CHURCH_PRO
    assert get_commercial_plan("everything_unlimited") is None


def test_owner_types_match_product_scope():
    assert PASTOR_PRO.owner_type == OWNER_TYPE_INDIVIDUAL
    assert CHURCH.owner_type == OWNER_TYPE_CHURCH
    assert CHURCH_PRO.owner_type == OWNER_TYPE_CHURCH


def test_all_metered_grants_have_positive_finite_limits():
    for plan in COMMERCIAL_PLANS:
        for grant in plan.entitlements:
            if grant.usage_period is None:
                continue

            assert grant.usage_limit is not None
            assert grant.usage_limit > 0
            assert grant.usage_period in {"daily", "monthly"}


def test_pastor_pro_expands_free_pastor_ai_capacity():
    grants = _grant_map(PASTOR_PRO)

    free_pastor = {
        grant.entitlement_key: grant
        for grant in FREE_PASTOR_GRANTS
    }

    assert (
        grants[ENTITLEMENT_XYNIVA_CHAT].usage_limit
        > free_pastor[ENTITLEMENT_XYNIVA_CHAT].usage_limit
    )

    assert (
        grants[ENTITLEMENT_SERMON_STUDIO].usage_limit
        > free_pastor[ENTITLEMENT_SERMON_STUDIO].usage_limit
    )


def test_pastor_pro_unlocks_advanced_individual_capabilities():
    grants = _grant_map(PASTOR_PRO)

    assert ENTITLEMENT_XYNIVA_ADVANCED_MEMORY in grants
    assert ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS in grants
    assert ENTITLEMENT_SERMON_STUDIO_ADVANCED in grants


def test_church_plan_contains_core_church_capability():
    grants = _grant_map(CHURCH)

    assert ENTITLEMENT_CHURCH_SPACE in grants


def test_church_pro_is_strict_capability_superset_of_church():
    church = set(_grant_map(CHURCH))
    church_pro = set(_grant_map(CHURCH_PRO))

    assert church < church_pro


def test_church_pro_has_more_xyniva_capacity_than_church():
    church = _grant_map(CHURCH)
    church_pro = _grant_map(CHURCH_PRO)

    assert (
        church_pro[ENTITLEMENT_XYNIVA_CHAT].usage_limit
        > church[ENTITLEMENT_XYNIVA_CHAT].usage_limit
    )


def test_church_pro_unlocks_intelligence_features():
    grants = _grant_map(CHURCH_PRO)

    assert ENTITLEMENT_CHURCH_INTELLIGENCE in grants
    assert ENTITLEMENT_MINISTRY_BRIEF in grants


def test_church_basic_does_not_receive_pro_intelligence_features():
    grants = _grant_map(CHURCH)

    assert ENTITLEMENT_CHURCH_INTELLIGENCE not in grants
    assert ENTITLEMENT_MINISTRY_BRIEF not in grants
