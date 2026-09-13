"""
XynaFaith V2 product entitlement vocabulary.

Entitlements describe product capabilities. Routes and services should
ask whether an effective access profile grants an entitlement rather
than checking subscription-plan names directly.
"""

# ============================================================
# XYNAFAITH / XYNIVA
# ============================================================

ENTITLEMENT_XYNIVA_CHAT = "xyniva.chat"
ENTITLEMENT_XYNIVA_MEMORY = "xyniva.memory"
ENTITLEMENT_XYNIVA_ADVANCED_MEMORY = "xyniva.memory.advanced"
ENTITLEMENT_XYNIVA_ACTIONS = "xyniva.actions"
ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS = "xyniva.actions.advanced"

# ============================================================
# SERMON / MINISTRY AI
# ============================================================

ENTITLEMENT_SERMON_STUDIO = "sermon.studio"
ENTITLEMENT_SERMON_STUDIO_ADVANCED = "sermon.studio.advanced"
ENTITLEMENT_BIBLICAL_RESEARCH = "biblical_research"
ENTITLEMENT_SERMON_SERIES = "sermon.series"
ENTITLEMENT_CONTENT_ENGINE = "content.engine"
ENTITLEMENT_DEVOTIONAL_STUDIO = "devotional.studio"
ENTITLEMENT_BIBLE_STUDY_STUDIO = "bible_study.studio"

# ============================================================
# MEMBER / COMMUNITY
# ============================================================

ENTITLEMENT_PRAYER_WALL = "prayer.wall"
ENTITLEMENT_TESTIMONY_WALL = "testimony.wall"
ENTITLEMENT_READING_PLANS = "reading_plans"
ENTITLEMENT_MEMBER_SERMON_NOTES = "member.sermon_notes"
ENTITLEMENT_SHARING = "sharing"
ENTITLEMENT_PASTOR_NETWORK = "pastor.network"

# ============================================================
# CHURCH
# ============================================================

ENTITLEMENT_CHURCH_SPACE = "church.space"
ENTITLEMENT_CHURCH_MEMBERS = "church.members"
ENTITLEMENT_PASTORAL_CARE = "church.pastoral_care"
ENTITLEMENT_ANNOUNCEMENTS = "church.announcements"
ENTITLEMENT_EVENTS = "church.events"
ENTITLEMENT_CHURCH_INTELLIGENCE = "church.intelligence"
ENTITLEMENT_MINISTRY_BRIEF = "church.ministry_brief"

# ============================================================
# PLATFORM
# ============================================================

ENTITLEMENT_UNIVERSAL_SEARCH = "search.universal"
ENTITLEMENT_MULTILINGUAL = "platform.multilingual"


ALL_ENTITLEMENTS = frozenset(
    {
        ENTITLEMENT_XYNIVA_CHAT,
        ENTITLEMENT_XYNIVA_MEMORY,
        ENTITLEMENT_XYNIVA_ADVANCED_MEMORY,
        ENTITLEMENT_XYNIVA_ACTIONS,
        ENTITLEMENT_XYNIVA_ADVANCED_ACTIONS,
        ENTITLEMENT_SERMON_STUDIO,
        ENTITLEMENT_SERMON_STUDIO_ADVANCED,
        ENTITLEMENT_BIBLICAL_RESEARCH,
        ENTITLEMENT_SERMON_SERIES,
        ENTITLEMENT_CONTENT_ENGINE,
        ENTITLEMENT_DEVOTIONAL_STUDIO,
        ENTITLEMENT_BIBLE_STUDY_STUDIO,
        ENTITLEMENT_PRAYER_WALL,
        ENTITLEMENT_TESTIMONY_WALL,
        ENTITLEMENT_READING_PLANS,
        ENTITLEMENT_MEMBER_SERMON_NOTES,
        ENTITLEMENT_SHARING,
        ENTITLEMENT_PASTOR_NETWORK,
        ENTITLEMENT_CHURCH_SPACE,
        ENTITLEMENT_CHURCH_MEMBERS,
        ENTITLEMENT_PASTORAL_CARE,
        ENTITLEMENT_ANNOUNCEMENTS,
        ENTITLEMENT_EVENTS,
        ENTITLEMENT_CHURCH_INTELLIGENCE,
        ENTITLEMENT_MINISTRY_BRIEF,
        ENTITLEMENT_UNIVERSAL_SEARCH,
        ENTITLEMENT_MULTILINGUAL,
    }
)


def is_known_entitlement(entitlement: str) -> bool:
    """Return True only for registered product entitlements."""
    return entitlement in ALL_ENTITLEMENTS
