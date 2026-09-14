"""
Effective Access Engine tests.
"""


import pytest

from api.services.effective_access_service import (
    get_effective_access,
    has_entitlement,
)


class DummyUser:

    def __init__(
        self,
        id=1,
        role="member",
    ):
        self.id = id
        self.role = role



def test_member_access():

    user = DummyUser(
        role="member"
    )

    result = get_effective_access(
        None,
        user=user,
    )

    assert result.user_id == 1

    assert result.role == "member"

    assert result.source_profile == (
        "baseline"
    )



def test_pastor_access():

    user = DummyUser(
        role="pastor"
    )

    result = get_effective_access(
        None,
        user=user,
    )

    assert result.role == "pastor"

    assert result.access_profile



def test_missing_subscription_is_safe():

    user = DummyUser()

    assert has_entitlement(
        None,
        user=user,
        entitlement_key="does.not.exist",
    ) is False
