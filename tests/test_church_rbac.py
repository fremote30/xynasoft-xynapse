"""
XynaFaith V2 Church Space RBAC contract tests.
"""

import pytest

from api.core.church_rbac import (
    CHURCH_ROLE_OWNER,
    CHURCH_ROLE_ADMIN,
    CHURCH_ROLE_PASTOR,
    CHURCH_ROLE_MINISTRY_LEADER,
    CHURCH_ROLE_GROUP_LEADER,
    CHURCH_ROLE_MEMBER,
    PERMISSION_CHURCH_VIEW,
    PERMISSION_CHURCH_MANAGE,
    PERMISSION_MEMBERS_VIEW,
    PERMISSION_MEMBERS_MANAGE,
    PERMISSION_CONTENT_CREATE,
    PERMISSION_CONTENT_MANAGE,
    PERMISSION_PRAYER_VIEW,
    PERMISSION_PASTORAL_CARE_MANAGE,
    PERMISSION_ANALYTICS_VIEW,
    role_has_permission,
)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (CHURCH_ROLE_OWNER, PERMISSION_CHURCH_MANAGE),
        (CHURCH_ROLE_OWNER, PERMISSION_MEMBERS_MANAGE),
        (CHURCH_ROLE_ADMIN, PERMISSION_CHURCH_MANAGE),
        (CHURCH_ROLE_ADMIN, PERMISSION_MEMBERS_MANAGE),
        (CHURCH_ROLE_PASTOR, PERMISSION_MEMBERS_VIEW),
        (CHURCH_ROLE_PASTOR, PERMISSION_CONTENT_MANAGE),
        (CHURCH_ROLE_PASTOR, PERMISSION_PASTORAL_CARE_MANAGE),
        (CHURCH_ROLE_PASTOR, PERMISSION_ANALYTICS_VIEW),
        (CHURCH_ROLE_MINISTRY_LEADER, PERMISSION_CONTENT_CREATE),
        (CHURCH_ROLE_MINISTRY_LEADER, PERMISSION_PRAYER_VIEW),
        (CHURCH_ROLE_GROUP_LEADER, PERMISSION_CONTENT_CREATE),
        (CHURCH_ROLE_GROUP_LEADER, PERMISSION_PRAYER_VIEW),
        (CHURCH_ROLE_MEMBER, PERMISSION_CHURCH_VIEW),
        (CHURCH_ROLE_MEMBER, PERMISSION_PRAYER_VIEW),
    ],
)
def test_role_allows_expected_permission(role, permission):
    assert role_has_permission(role, permission)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (CHURCH_ROLE_MEMBER, PERMISSION_CHURCH_MANAGE),
        (CHURCH_ROLE_MEMBER, PERMISSION_MEMBERS_MANAGE),
        (CHURCH_ROLE_MEMBER, PERMISSION_CONTENT_CREATE),
        (CHURCH_ROLE_MEMBER, PERMISSION_PASTORAL_CARE_MANAGE),
        (CHURCH_ROLE_GROUP_LEADER, PERMISSION_MEMBERS_MANAGE),
        (CHURCH_ROLE_GROUP_LEADER, PERMISSION_CONTENT_MANAGE),
        (
            CHURCH_ROLE_MINISTRY_LEADER,
            PERMISSION_PASTORAL_CARE_MANAGE,
        ),
        (CHURCH_ROLE_PASTOR, PERMISSION_CHURCH_MANAGE),
        (CHURCH_ROLE_PASTOR, PERMISSION_MEMBERS_MANAGE),
    ],
)
def test_role_denies_ungranted_permission(role, permission):
    assert not role_has_permission(role, permission)


def test_unknown_role_fails_closed():
    assert not role_has_permission(
        "unknown-role",
        PERMISSION_CHURCH_VIEW,
    )


def test_legacy_platform_admin_is_not_church_role():
    assert not role_has_permission(
        "platform_admin",
        PERMISSION_CHURCH_MANAGE,
    )


def test_unknown_permission_fails_closed():
    assert not role_has_permission(
        CHURCH_ROLE_OWNER,
        "church.superuser",
    )
