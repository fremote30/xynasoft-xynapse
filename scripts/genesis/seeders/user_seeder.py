from datetime import datetime
import re
import unicodedata

from api.core.security import hash_password
from api.models.church import Church
from api.models.pastor_profile import PastorProfile
from api.models.user import User
from scripts.genesis.utils import result


def slugify(value: str) -> str:
    """
    Convert a name into a URL-safe slug.

    Example:
        "Pastor Samuel Mensah" -> "samuel-mensah"
    """
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()

    if value.startswith("pastor "):
        value = value[len("pastor ") :]

    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def seed_users(db, records, dry_run):
    """
    Seed Genesis users and ensure every pastor has a PastorProfile.

    The seeder is idempotent:
    - Existing users are not duplicated.
    - Existing pastor profiles are not duplicated.
    - Missing pastor profiles are created on later runs.
    """

    out = result()

    for record in records:
        email = record["email"].strip().lower()
        role = record["role"].strip().lower()
        is_pastor = role == "pastor"

        church = (
            db.query(Church)
            .filter(Church.name == record["church"])
            .first()
        )

        if church is None:
            out["skipped"] += 1
            continue

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if user is None:
            user = User(
                name=record["name"],
                email=email,
                password=hash_password(record["password"]),
                role=role,
                is_verified=True,
                church_id=church.id,
                pastor_status="approved" if is_pastor else "member",
                pastor_application_date=(
                    datetime.utcnow() if is_pastor else None
                ),
                pastor_review_date=(
                    datetime.utcnow() if is_pastor else None
                ),
                pastor_review_notes=(
                    "Genesis Community seed account"
                    if is_pastor
                    else None
                ),
            )

            out["created"] += 1

            if dry_run:
                continue

            db.add(user)
            db.flush()

        else:
            out["existing"] += 1

        if user.role != "pastor":
            continue

        profile = (
            db.query(PastorProfile)
            .filter(PastorProfile.user_id == user.id)
            .first()
        )

        if profile is not None:
            continue

        if dry_run:
            continue

        profile = PastorProfile(
            user_id=user.id,
            church_name=church.name,
            denomination=church.denomination or "",
            city=church.city or "",
            country=church.country or "",
            location=church.location or "",
            bio=f"{user.name} serves the {church.name} community.",
            mission_statement=(
                "To proclaim Christ, disciple believers, "
                "and serve the local community."
            ),
            ministry_focus="Biblical Teaching",
            church_size="Growing",
            specialties="Preaching, Discipleship",
            years_in_ministry=10,
            favorite_scripture="John 3:16",
            accepts_prayer_requests=True,
            allow_direct_messages=True,
            is_verified=True,
            is_public=True,
            visibility="public",
            slug=slugify(user.name),
        )

        db.add(profile)
        db.flush()

    if not dry_run:
        db.flush()

    return out