from api.core.church_rbac import (
    CHURCH_ROLE_ADMIN,
    CHURCH_ROLE_GROUP_LEADER,
    CHURCH_ROLE_MEMBER,
    CHURCH_ROLE_MINISTRY_LEADER,
    CHURCH_ROLE_OWNER,
    CHURCH_ROLE_PASTOR,
    PERMISSION_GROUPS_MANAGE,
    role_has_permission,
)
from api.core.entitlements import (
    ALL_ENTITLEMENTS,
    ENTITLEMENT_CHURCH_GROUPS,
)
from api.core.product_catalog import (
    CHURCH,
    CHURCH_PRO,
    PASTOR_PRO,
)
from api.models.church_group import (
    GROUP_MEMBER_ROLES,
    GROUP_MEMBER_STATUSES,
    GROUP_STATUSES,
    GROUP_TYPES,
)


def _entitlement_names(plan):
    return {grant.entitlement_key for grant in plan.entitlements}


def test_group_domain_contracts_are_registered():
    assert GROUP_TYPES == {
        "ministry",
        "small_group",
        "team",
        "class",
        "other",
    }
    assert GROUP_STATUSES == {
        "active",
        "inactive",
        "archived",
    }
    assert GROUP_MEMBER_ROLES == {
        "leader",
        "co_leader",
        "member",
    }
    assert GROUP_MEMBER_STATUSES == {
        "invited",
        "active",
        "left",
    }


def test_only_church_wide_managers_receive_groups_manage():
    assert role_has_permission(CHURCH_ROLE_OWNER, PERMISSION_GROUPS_MANAGE)
    assert role_has_permission(CHURCH_ROLE_ADMIN, PERMISSION_GROUPS_MANAGE)
    assert role_has_permission(CHURCH_ROLE_PASTOR, PERMISSION_GROUPS_MANAGE)

    assert not role_has_permission(
        CHURCH_ROLE_MINISTRY_LEADER,
        PERMISSION_GROUPS_MANAGE,
    )
    assert not role_has_permission(
        CHURCH_ROLE_GROUP_LEADER,
        PERMISSION_GROUPS_MANAGE,
    )
    assert not role_has_permission(
        CHURCH_ROLE_MEMBER,
        PERMISSION_GROUPS_MANAGE,
    )


def test_church_groups_is_known_commercial_entitlement():
    assert ENTITLEMENT_CHURCH_GROUPS == "church.groups"
    assert ENTITLEMENT_CHURCH_GROUPS in ALL_ENTITLEMENTS


def test_church_plans_receive_groups_but_pastor_pro_does_not():
    assert ENTITLEMENT_CHURCH_GROUPS in _entitlement_names(CHURCH)
    assert ENTITLEMENT_CHURCH_GROUPS in _entitlement_names(CHURCH_PRO)
    assert ENTITLEMENT_CHURCH_GROUPS not in _entitlement_names(PASTOR_PRO)
