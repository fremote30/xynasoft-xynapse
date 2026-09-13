"""
XynaFaith V2 monetization vocabulary tests.
"""

from api.core.access_profiles import (
    ACCESS_PROFILE_FREE_MEMBER,
    ACCESS_PROFILE_FREE_PASTOR,
    ACCESS_PROFILE_PASTOR_PRO,
    ACCESS_PROFILE_CHURCH,
    ACCESS_PROFILE_CHURCH_PRO,
    ALL_ACCESS_PROFILES,
    is_known_access_profile,
)

from api.core.entitlements import (
    ALL_ENTITLEMENTS,
    ENTITLEMENT_XYNIVA_CHAT,
    ENTITLEMENT_SERMON_STUDIO,
    ENTITLEMENT_PASTORAL_CARE,
    ENTITLEMENT_MULTILINGUAL,
    is_known_entitlement,
)


def test_access_profiles_are_unique():
    assert len(ALL_ACCESS_PROFILES) == 5


def test_expected_access_profiles_exist():
    assert ACCESS_PROFILE_FREE_MEMBER in ALL_ACCESS_PROFILES
    assert ACCESS_PROFILE_FREE_PASTOR in ALL_ACCESS_PROFILES
    assert ACCESS_PROFILE_PASTOR_PRO in ALL_ACCESS_PROFILES
    assert ACCESS_PROFILE_CHURCH in ALL_ACCESS_PROFILES
    assert ACCESS_PROFILE_CHURCH_PRO in ALL_ACCESS_PROFILES


def test_unknown_access_profile_fails_closed():
    assert is_known_access_profile("free_member")
    assert not is_known_access_profile("super_unlimited")


def test_entitlements_are_unique():
    assert len(ALL_ENTITLEMENTS) == len(set(ALL_ENTITLEMENTS))


def test_core_v2_entitlements_exist():
    assert ENTITLEMENT_XYNIVA_CHAT in ALL_ENTITLEMENTS
    assert ENTITLEMENT_SERMON_STUDIO in ALL_ENTITLEMENTS
    assert ENTITLEMENT_PASTORAL_CARE in ALL_ENTITLEMENTS
    assert ENTITLEMENT_MULTILINGUAL in ALL_ENTITLEMENTS


def test_unknown_entitlement_fails_closed():
    assert is_known_entitlement("xyniva.chat")
    assert not is_known_entitlement("everything.unlimited")
