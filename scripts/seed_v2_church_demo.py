"""
Development-only XynaFaith V2 Church Space fixture.

Never run against production.
Creates a fictional church and two dedicated test accounts.
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


CHURCH_NAME = "Genesis Community Church — V2 Demo"

ACCOUNTS = (
    ("v2.church.owner@example.test", "V2 Demo Church Owner", "owner"),
    ("v2.church.member@example.test", "V2 Demo Church Member", "member"),
)


def main():
    if os.getenv("XYNAFAITH_V2_ALLOW_DEMO_SEED") != "yes":
        raise SystemExit(
            "STOP: Explicit development fixture authorization required."
        )

    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        raise SystemExit("STOP: DATABASE_URL is missing.")

    url = make_url(raw_url)

    if url.database != "xynafaith_v2" or url.host != "db":
        raise SystemExit("STOP: Unexpected database target.")

    credential_path = Path("/tmp/xynafaith-v2-demo-credentials.txt")

    if credential_path.exists():
        raise SystemExit(
            "STOP: Demo credential file already exists. "
            "Refusing to overwrite it."
        )

    credential_lines = []
    engine = create_engine(raw_url)

    with Session(engine) as db:
        with db.begin():
            church = (
                db.query(Church)
                .filter(Church.name == CHURCH_NAME)
                .one_or_none()
            )

            if church is None:
                church = Church(
                    name=CHURCH_NAME,
                    location="Development Demo",
                    denomination="General",
                    country="Demo",
                    city="Demo City",
                    is_featured=False,
                    is_verified=False,
                )
                db.add(church)
                db.flush()
                print("Created demo church:", church.id)
            else:
                print("Reusing demo church:", church.id)

            for email, name, role in ACCOUNTS:
                user = (
                    db.query(User)
                    .filter(User.email == email)
                    .one_or_none()
                )

                if user is None:
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
                    print(f"Created {role} user ID: {user.id}")
                    credential_lines.append(
                        f"{email}:{password}"
                    )
                else:
                    print(f"Reusing {role} user ID: {user.id}")

                membership = (
                    db.query(ChurchMembership)
                    .filter(
                        ChurchMembership.church_id == church.id,
                        ChurchMembership.user_id == user.id,
                    )
                    .one_or_none()
                )

                if membership is None:
                    other_primary = (
                        db.query(ChurchMembership)
                        .filter(
                            ChurchMembership.user_id == user.id,
                            ChurchMembership.is_primary.is_(True),
                        )
                        .first()
                    )

                    if other_primary:
                        raise RuntimeError(
                            "STOP: Demo user already has another "
                            "primary church."
                        )

                    db.add(
                        ChurchMembership(
                            church_id=church.id,
                            user_id=user.id,
                            role=role,
                            status="active",
                            is_primary=True,
                        )
                    )
                    print(f"Created {role} membership")
                else:
                    if (
                        membership.role != role
                        or membership.status != "active"
                        or not membership.is_primary
                    ):
                        raise RuntimeError(
                            "STOP: Existing demo membership differs "
                            "from expected configuration."
                        )
                    print(f"Reusing {role} membership")

            # Store initial credentials before committing database changes.
            # The file is private to the development container.
            if credential_lines:
                descriptor = os.open(
                    credential_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(descriptor, "w") as output:
                    output.write("\\n".join(credential_lines) + "\\n")

                print("Initial credentials saved privately.")

    print("PASS: V2 demo fixture transaction completed")


if __name__ == "__main__":
    main()
