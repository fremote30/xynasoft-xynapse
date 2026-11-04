"""
XynaFaith V2 access-profile contracts.

Free access is role-aware. Paid subscriptions can replace or augment
the effective access profile through the entitlement service.

These identifiers are internal product contracts and should not be
used as payment-provider product IDs.
"""

ACCESS_PROFILE_FREE_MEMBER = "free_member"
ACCESS_PROFILE_FREE_PASTOR = "free_pastor"
ACCESS_PROFILE_PASTOR_PRO = "pastor_pro"
ACCESS_PROFILE_CHURCH = "church"
ACCESS_PROFILE_CHURCH_PRO = "church_pro"


ALL_ACCESS_PROFILES = frozenset(
    {
        ACCESS_PROFILE_FREE_MEMBER,
        ACCESS_PROFILE_FREE_PASTOR,
        ACCESS_PROFILE_PASTOR_PRO,
        ACCESS_PROFILE_CHURCH,
        ACCESS_PROFILE_CHURCH_PRO,
    }
)


def is_known_access_profile(profile: str) -> bool:
    return profile in ALL_ACCESS_PROFILES
