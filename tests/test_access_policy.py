from api.core.access_policy import (
    FREE_MEMBER_GRANTS,
    FREE_PASTOR_GRANTS,
    baseline_grants,
    baseline_profile_for_role,
)
from api.core.access_profiles import (
    ACCESS_PROFILE_FREE_MEMBER,
    ACCESS_PROFILE_FREE_PASTOR,
)
from api.core.entitlements import (
    ENTITLEMENT_SERMON_STUDIO,
    ENTITLEMENT_XYNIVA_CHAT,
)


def _grant_map(grants):
    return {
        grant.entitlement_key: grant
        for grant in grants
    }


def test_member_resolves_to_free_member():
    assert (
        baseline_profile_for_role("member")
        == ACCESS_PROFILE_FREE_MEMBER
    )


def test_pastor_resolves_to_free_pastor():
    assert (
        baseline_profile_for_role("pastor")
        == ACCESS_PROFILE_FREE_PASTOR
    )


def test_unknown_role_fails_to_member_baseline():
    assert (
        baseline_profile_for_role("something_unknown")
        == ACCESS_PROFILE_FREE_MEMBER
    )


def test_none_role_fails_to_member_baseline():
    assert (
        baseline_profile_for_role(None)
        == ACCESS_PROFILE_FREE_MEMBER
    )


def test_free_member_has_capped_xyniva():
    grants = _grant_map(FREE_MEMBER_GRANTS)

    grant = grants[ENTITLEMENT_XYNIVA_CHAT]

    assert grant.enabled is True
    assert grant.usage_limit is not None
    assert grant.usage_limit > 0
    assert grant.usage_period == "monthly"


def test_free_member_does_not_receive_sermon_studio():
    grants = _grant_map(FREE_MEMBER_GRANTS)

    assert ENTITLEMENT_SERMON_STUDIO not in grants


def test_free_pastor_receives_sermon_studio():
    grants = _grant_map(FREE_PASTOR_GRANTS)

    grant = grants[ENTITLEMENT_SERMON_STUDIO]

    assert grant.enabled is True
    assert grant.usage_limit is not None
    assert grant.usage_limit > 0


def test_free_pastor_keeps_xyniva():
    grants = _grant_map(FREE_PASTOR_GRANTS)

    assert ENTITLEMENT_XYNIVA_CHAT in grants


def test_free_pastor_is_more_capable_than_free_member():
    member = set(_grant_map(FREE_MEMBER_GRANTS))
    pastor = set(_grant_map(FREE_PASTOR_GRANTS))

    assert member < pastor


def test_unknown_profile_fails_closed():
    assert baseline_grants("unlimited_everything") == ()


def test_free_profiles_have_no_duplicate_entitlements():
    member_keys = [
        grant.entitlement_key
        for grant in FREE_MEMBER_GRANTS
    ]
    pastor_keys = [
        grant.entitlement_key
        for grant in FREE_PASTOR_GRANTS
    ]

    assert len(member_keys) == len(set(member_keys))
    assert len(pastor_keys) == len(set(pastor_keys))


def test_free_pastor_has_larger_xyniva_allowance():
    member = _grant_map(FREE_MEMBER_GRANTS)
    pastor = _grant_map(FREE_PASTOR_GRANTS)

    assert (
        pastor[ENTITLEMENT_XYNIVA_CHAT].usage_limit
        > member[ENTITLEMENT_XYNIVA_CHAT].usage_limit
    )
