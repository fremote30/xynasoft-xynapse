"""
XynaFaith V2: development-only multi-church demo fixture.

15 churches, 15 pastors, 200 members.
Refuses unexpected database targets.
Does not modify existing unrelated users.
"""

import os
import secrets
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.core.security import hash_password
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.user import User


CHURCHES = [
    ("Genesis Community Church", "Accra"),
    ("Grace Fellowship Chapel", "Kumasi"),
    ("Living Hope Assembly", "Cape Coast"),
    ("New Covenant Community", "Tamale"),
    ("Faith Harbour Church", "Takoradi"),
    ("Kingdom Life Fellowship", "Tema"),
    ("Hope Springs Chapel", "Koforidua"),
    ("Victory Community Church", "Ho"),
    ("Restoration Faith Assembly", "Sunyani"),
    ("Cornerstone Fellowship", "Bolgatanga"),
    ("New Life Community Chapel", "Wa"),
    ("Harvest Grace Church", "Techiman"),
    ("Peace River Fellowship", "Obuasi"),
    ("Light of Hope Chapel", "Kasoa"),
    ("Unity Christian Community", "Winneba"),
]

TOTAL_MEMBERS = 200
DOMAIN = "v2-demo.invalid"
CREDENTIAL_FILE = Path("/tmp/xynafaith-v2-multi-church-credentials.txt")


def main():
    if os.getenv("XYNAFAITH_V2_ALLOW_DEMO_SEED") != "yes":
        raise SystemExit("STOP: Explicit seed authorization required")

    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        raise SystemExit("STOP: DATABASE_URL missing")

    url = make_url(raw_url)

    if url.database != "xynafaith_v2" or url.host != "db":
        raise SystemExit("STOP: Unexpected database target")

    if CREDENTIAL_FILE.exists():
        raise SystemExit("STOP: Credential file already exists")

    engine = create_engine(raw_url)

    # Keep credentials available only in the V2 container.
    credentials = []
    counts = {"churches": 0, "pastors": 0, "members": 0}

    def ensure_user(db, email, name):
        user = db.query(User).filter(User.email == email).one_or_none()

        if user:
            if user.name != name:
                raise RuntimeError("STOP: Existing demo identity conflict")
            return user

        password = secrets.token_urlsafe(24)

        user = User(
            name=name,
            email=email,
            password=hash_password(password),
            role="member",
            is_verified=True,
        )

        db.add(user)
        db.flush()
        credentials.append((email, password))
        return user

    def ensure_membership(db, church, user, role):
        membership = (
            db.query(ChurchMembership)
            .filter(
                ChurchMembership.church_id == church.id,
                ChurchMembership.user_id == user.id,
            )
            .one_or_none()
        )

        if membership:
            if (
                membership.role != role
                or membership.status != "active"
                or not membership.is_primary
            ):
                raise RuntimeError("STOP: Conflicting demo membership")
            return

        primary = (
            db.query(ChurchMembership)
            .filter(
                ChurchMembership.user_id == user.id,
                ChurchMembership.is_primary.is_(True),
            )
            .first()
        )

        if primary:
            raise RuntimeError("STOP: User has another primary church")

        db.add(
            ChurchMembership(
                church_id=church.id,
                user_id=user.id,
                role=role,
                status="active",
                is_primary=True,
            )
        )

    try:
        with Session(engine) as db:
            with db.begin():
                for index, (name, city) in enumerate(CHURCHES, 1):
                    church_name = f"{name} — V2 Demo"

                    church = (
                        db.query(Church)
                        .filter(Church.name == church_name)
                        .one_or_none()
                    )

                    if church is None:
                        church = Church(
                            name=church_name,
                            location=f"{city}, Ghana",
                            city=city,
                            country="Ghana",
                            denomination="General",
                            is_verified=False,
                            is_featured=False,
                        )
                        db.add(church)
                        db.flush()

                    counts["churches"] += 1

                    pastor = ensure_user(
                        db,
                        f"pastor{index:02d}@{DOMAIN}",
                        f"Demo Pastor {index:02d}",
                    )
                    ensure_membership(db, church, pastor, "pastor")
                    counts["pastors"] += 1

                    # 200 members distributed across 15 churches.
                    member_count = (
                        14 if index <= 5 else 13
                    )

                    start = sum(
                        14 if i <= 5 else 13
                        for i in range(1, index)
                    )

                    for offset in range(member_count):
                        number = start + offset + 1

                        member = ensure_user(
                            db,
                            f"member{number:03d}@{DOMAIN}",
                            f"Demo Member {number:03d}",
                        )

                        ensure_membership(db, church, member, "member")
                        counts["members"] += 1

                if counts != {
                    "churches": 15,
                    "pastors": 15,
                    "members": TOTAL_MEMBERS,
                }:
                    raise RuntimeError("STOP: Demo counts incorrect")

                if credentials:
                    fd = os.open(
                        CREDENTIAL_FILE,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                    )
                    with os.fdopen(fd, "w") as file:
                        for email, password in credentials:
                            file.write(f"{email}:{password}\n")

        print("PASS: Multi-church fixture transaction completed")
        print("Churches:", counts["churches"])
        print("Pastors:", counts["pastors"])
        print("Members:", counts["members"])
        print("Credentials stored privately inside V2 container")

    except Exception:
        # Credential files and database transactions are not atomic.
        # Preserve the file for recovery if it was created.
        print("STOP: Fixture failed; inspect state before retrying")
        raise


if __name__ == "__main__":
    main()
