"""Development-only XynaFaith V2 community content fixture."""

import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.church_announcement import ChurchAnnouncement
from api.models.church_event import ChurchEvent
from api.models.church_group import ChurchGroup
from api.models.prayer import Prayer, PrayerRecipient
from api.models.pastoral_care_case import PastoralCareCase
from api.models.pastoral_care_activity import PastoralCareActivity

PREFIX = "[V2 DEMO]"
DOMAIN = "@v2-demo.invalid"
WRITE = os.getenv("XYNAFAITH_V2_CONTENT_WRITE") == "yes"

url = make_url(os.environ["DATABASE_URL"])

if url.host != "db" or url.database != "xynafaith_v2":
    raise SystemExit("STOP: Unexpected database target")

if WRITE and os.getenv("XYNAFAITH_V2_ALLOW_DEMO_SEED") != "yes":
    raise SystemExit("STOP: Explicit demo seed authorization required")

engine = create_engine(url)
now = datetime.utcnow()

announcement_titles = [
    "Welcome to Our Church Community",
    "Weekly Fellowship and Prayer",
    "Community Outreach Update",
]

event_titles = [
    "Sunday Worship Gathering",
    "Midweek Bible Study",
    "Community Service Day",
]

prayer_messages = [
    "Please pray for wisdom and guidance this week.",
    "Giving thanks for renewed hope and encouragement.",
    "Please pray for our community and its families.",
    "Thankful for an answered prayer and renewed strength.",
    "Please pray for peace and continued unity.",
]

def find_one(db, model, **filters):
    return db.query(model).filter_by(**filters).one_or_none()

def create_if_missing(db, model, lookup, values):
    existing = find_one(db, model, **lookup)
    if existing is not None:
        return existing, False

    obj = model(**lookup, **values)
    db.add(obj)
    db.flush()
    return obj, True

def main():
    with Session(engine) as db:
        churches = (
            db.query(Church)
            .filter(Church.name.like("% — V2 Demo"))
            .order_by(Church.id)
            .all()
        )

        if len(churches) != 15:
            raise SystemExit("STOP: Expected exactly 15 demo churches")

        plans = []

        for church in churches:
            memberships = (
                db.query(ChurchMembership)
                .join(User, User.id == ChurchMembership.user_id)
                .filter(
                    ChurchMembership.church_id == church.id,
                    ChurchMembership.status == "active",
                    ChurchMembership.is_primary.is_(True),
                    User.email.like(f"%{DOMAIN}"),
                )
                .all()
            )

            pastors = [m for m in memberships if m.role == "pastor"]
            members = sorted(
                [m for m in memberships if m.role == "member"],
                key=lambda m: m.user_id,
            )

            if len(pastors) != 1 or len(members) not in (13, 14):
                raise SystemExit(
                    f"STOP: Unexpected membership configuration for {church.id}"
                )

            plans.append((church, pastors[0], members))

        if not WRITE:
            print("PASS: Dry-run validation completed")
            print("Churches:", len(plans))
            print("Planned announcements: 45")
            print("Planned events: 45")
            print("Planned prayers: 75")
            print("Planned pending testimonies: 30")
            print("Planned pastoral-care cases: 30")
            print("Planned groups: 30")
            print("Database unchanged")
            return

        created = {
            "announcements": 0,
            "events": 0,
            "groups": 0,
            "prayers": 0,
            "recipients": 0,
            "care_cases": 0,
            "care_activities": 0,
        }

        with db.begin_nested():
            for church, pastor, members in plans:
                # Groups
                for index, (label, kind) in enumerate([
                    ("Community Small Group", "small_group"),
                    ("Outreach Ministry", "ministry"),
                ]):
                    _, added = create_if_missing(
                        db,
                        ChurchGroup,
                        {
                            "church_id": church.id,
                            "name": f"{PREFIX} {label}",
                        },
                        {
                            "description": "Fictional V2 demonstration group.",
                            "group_type": kind,
                            "status": "active",
                        },
                    )
                    created["groups"] += int(added)

                # Announcements
                for index, title in enumerate(announcement_titles):
                    status = ["published", "published", "draft"][index]
                    _, added = create_if_missing(
                        db,
                        ChurchAnnouncement,
                        {
                            "church_id": church.id,
                            "title": f"{PREFIX} {title}",
                        },
                        {
                            "author_user_id": pastor.user_id,
                            "body": (
                                "Fictional church announcement for "
                                "XynaFaith V2 interface testing."
                            ),
                            "status": status,
                            "published_at": now if status == "published" else None,
                        },
                    )
                    created["announcements"] += int(added)

                # Events
                for index, title in enumerate(event_titles):
                    status = ["published", "published", "draft"][index]
                    start = now + timedelta(days=7 + index * 7)
                    _, added = create_if_missing(
                        db,
                        ChurchEvent,
                        {
                            "church_id": church.id,
                            "title": f"{PREFIX} {title}",
                        },
                        {
                            "created_by_user_id": pastor.user_id,
                            "description": "Fictional V2 demonstration event.",
                            "starts_at": start,
                            "ends_at": start + timedelta(hours=2),
                            "location": "Church community hall",
                            "status": status,
                            "published_at": now if status == "published" else None,
                        },
                    )
                    created["events"] += int(added)

                # Five prayers per church:
                # 2 answered with pending testimonies,
                # 2 private pastoral-care requests,
                # 1 ordinary community prayer.
                for index in range(5):
                    member = members[index]
                    is_care = index in (2, 3)
                    is_answered = index in (0, 1)

                    message = (
                        f"{PREFIX} Church {church.id} prayer {index + 1}. "
                        f"{prayer_messages[index]}"
                    )

                    prayer, added = create_if_missing(
                        db,
                        Prayer,
                        {
                            "church_id": church.id,
                            "user_id": member.user_id,
                            "message": message,
                        },
                        {
                            "user_name": f"Demo Member {index + 1}",
                            "visibility": "private" if is_care else "community",
                            "status": "answered" if is_answered else "still_praying",
                            "pastoral_care_requested": is_care,
                            "is_anonymous": is_care,
                            "is_hidden": False,
                            "answer_testimony": (
                                "I am grateful for encouragement and "
                                "an answered prayer during this season."
                                if is_answered else None
                            ),
                            "answered_at": now if is_answered else None,
                            "testimony_status": "pending" if is_answered else None,
                            "testimony_shared_at": None,
                        },
                    )
                    created["prayers"] += int(added)

                    if not is_care:
                        continue

                    # Private recipient is from the SAME church.
                    _, recipient_added = create_if_missing(
                        db,
                        PrayerRecipient,
                        {
                            "prayer_id": prayer.id,
                            "recipient_user_id": pastor.user_id,
                        },
                        {"recipient_role": "pastor"},
                    )
                    created["recipients"] += int(recipient_added)

                    case, case_added = create_if_missing(
                        db,
                        PastoralCareCase,
                        {
                            "church_id": church.id,
                            "prayer_id": prayer.id,
                        },
                        {
                            "member_user_id": member.user_id,
                            "assigned_to_user_id": pastor.user_id,
                            "status": "open",
                            "priority": "routine",
                        },
                    )
                    created["care_cases"] += int(case_added)

                    _, activity_added = create_if_missing(
                        db,
                        PastoralCareActivity,
                        {
                            "case_id": case.id,
                            "church_id": church.id,
                            "activity_type": "case_created",
                        },
                        {"actor_user_id": member.user_id},
                    )
                    created["care_activities"] += int(activity_added)

            db.flush()

        db.commit()

        print("PASS: V2 community content transaction committed")
        for key, value in created.items():
            print(f"{key}: {value}")
        print("Existing records reused; no duplicate fixture entries created")

if __name__ == "__main__":
    main()
