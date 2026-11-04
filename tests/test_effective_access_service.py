"""
XynaFaith V2 Effective Access Engine tests.

Validates:
- baseline free access
- entitlement checks
- feature gates
- denied features
"""

from api.services.effective_access_service import (
    get_effective_access,
    has_entitlement,
    check_feature_gate,
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
        user,
    )

    assert result.access_profile == (
        "free_member"
    )

    assert (
        "xyniva.chat"
        in result.entitlements
    )



def test_entitlement_check():

    user = DummyUser()

    assert has_entitlement(
        None,
        user,
        "xyniva.chat",
    )



def test_missing_entitlement():

    user = DummyUser()

    assert has_entitlement(
        None,
        user,
        "does.not.exist",
    ) is False



def test_feature_gate_response():

    user = DummyUser()

    result = check_feature_gate(
        None,
        user,
        "xyniva.chat",
    )

    assert result.allowed is True

    assert result.entitlement_key == (
        "xyniva.chat"
    )

    assert result.reason == (
        "entitlement_granted"
    )



def test_unknown_feature_denied():

    user = DummyUser()

    result = check_feature_gate(
        None,
        user,
        "unknown.feature",
    )

    assert result.allowed is False

    assert result.reason == (
        "missing_entitlement"
    )
