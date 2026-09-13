"""
Central XynaFaith V2 Church Space RBAC contracts.

Global User.role remains available for V1 compatibility.
V2 Church Space authorization must use membership roles.
"""

CHURCH_ROLE_OWNER = "owner"
CHURCH_ROLE_ADMIN = "admin"
CHURCH_ROLE_PASTOR = "pastor"
CHURCH_ROLE_MINISTRY_LEADER = "ministry_leader"
CHURCH_ROLE_GROUP_LEADER = "group_leader"
CHURCH_ROLE_MEMBER = "member"

CHURCH_ROLES = frozenset(
    {
        CHURCH_ROLE_OWNER,
        CHURCH_ROLE_ADMIN,
        CHURCH_ROLE_PASTOR,
        CHURCH_ROLE_MINISTRY_LEADER,
        CHURCH_ROLE_GROUP_LEADER,
        CHURCH_ROLE_MEMBER,
    }
)

MEMBERSHIP_STATUS_INVITED = "invited"
MEMBERSHIP_STATUS_ACTIVE = "active"
MEMBERSHIP_STATUS_SUSPENDED = "suspended"
MEMBERSHIP_STATUS_LEFT = "left"

MEMBERSHIP_STATUSES = frozenset(
    {
        MEMBERSHIP_STATUS_INVITED,
        MEMBERSHIP_STATUS_ACTIVE,
        MEMBERSHIP_STATUS_SUSPENDED,
        MEMBERSHIP_STATUS_LEFT,
    }
)


PERMISSION_CHURCH_VIEW = "church.view"
PERMISSION_CHURCH_MANAGE = "church.manage"
PERMISSION_MEMBERS_VIEW = "members.view"
PERMISSION_MEMBERS_MANAGE = "members.manage"
PERMISSION_CONTENT_CREATE = "content.create"
PERMISSION_CONTENT_MANAGE = "content.manage"
PERMISSION_PRAYER_VIEW = "prayer.view"
PERMISSION_PASTORAL_CARE_MANAGE = "pastoral_care.manage"
PERMISSION_ANALYTICS_VIEW = "analytics.view"


ROLE_PERMISSIONS = {
    CHURCH_ROLE_OWNER: frozenset(
        {
            PERMISSION_CHURCH_VIEW,
            PERMISSION_CHURCH_MANAGE,
            PERMISSION_MEMBERS_VIEW,
            PERMISSION_MEMBERS_MANAGE,
            PERMISSION_CONTENT_CREATE,
            PERMISSION_CONTENT_MANAGE,
            PERMISSION_PRAYER_VIEW,
            PERMISSION_PASTORAL_CARE_MANAGE,
            PERMISSION_ANALYTICS_VIEW,
        }
    ),
    CHURCH_ROLE_ADMIN: frozenset(
        {
            PERMISSION_CHURCH_VIEW,
            PERMISSION_CHURCH_MANAGE,
            PERMISSION_MEMBERS_VIEW,
            PERMISSION_MEMBERS_MANAGE,
            PERMISSION_CONTENT_CREATE,
            PERMISSION_CONTENT_MANAGE,
            PERMISSION_PRAYER_VIEW,
            PERMISSION_PASTORAL_CARE_MANAGE,
            PERMISSION_ANALYTICS_VIEW,
        }
    ),
    CHURCH_ROLE_PASTOR: frozenset(
        {
            PERMISSION_CHURCH_VIEW,
            PERMISSION_MEMBERS_VIEW,
            PERMISSION_CONTENT_CREATE,
            PERMISSION_CONTENT_MANAGE,
            PERMISSION_PRAYER_VIEW,
            PERMISSION_PASTORAL_CARE_MANAGE,
            PERMISSION_ANALYTICS_VIEW,
        }
    ),
    CHURCH_ROLE_MINISTRY_LEADER: frozenset(
        {
            PERMISSION_CHURCH_VIEW,
            PERMISSION_MEMBERS_VIEW,
            PERMISSION_CONTENT_CREATE,
            PERMISSION_PRAYER_VIEW,
        }
    ),
    CHURCH_ROLE_GROUP_LEADER: frozenset(
        {
            PERMISSION_CHURCH_VIEW,
            PERMISSION_MEMBERS_VIEW,
            PERMISSION_CONTENT_CREATE,
            PERMISSION_PRAYER_VIEW,
        }
    ),
    CHURCH_ROLE_MEMBER: frozenset(
        {
            PERMISSION_CHURCH_VIEW,
            PERMISSION_PRAYER_VIEW,
        }
    ),
}


def role_has_permission(
    role: str,
    permission: str,
) -> bool:
    return permission in ROLE_PERMISSIONS.get(
        role,
        frozenset(),
    )
