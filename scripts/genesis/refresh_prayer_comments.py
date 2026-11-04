import argparse

from api.db.database import SessionLocal
from api.models.prayer import Prayer, PrayerComment
from api.models.user import User
from scripts.genesis.seeders.content_seeder import (
    PASTOR_ENCOURAGEMENTS,
    MEMBER_COMMENTS,
)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist Genesis prayer comment updates."
    )

    args = parser.parse_args()
    dry_run = not args.commit

    print("")
    print("========================================")
    print("Genesis Prayer Comment Refresh")
    print("========================================")
    print(
        "MODE:",
        "DRY RUN" if dry_run else "COMMIT"
    )
    print("")

    db = SessionLocal()

    try:

        prayers = (
            db.query(Prayer)
            .filter(
                Prayer.message.like(
                    "%[Genesis #%"
                )
            )
            .order_by(Prayer.id)
            .all()
        )

        genesis_users = (
            db.query(User)
            .filter(
                User.email.ilike(
                    "%@genesis.xynafaith.com"
                )
            )
            .order_by(User.id)
            .all()
        )

        genesis_pastors = [
            user
            for user in genesis_users
            if user.role == "pastor"
        ]

        genesis_members = [
            user
            for user in genesis_users
            if user.role != "pastor"
        ]

        print(
            "Genesis prayers:",
            len(prayers)
        )

        print(
            "Genesis pastors:",
            len(genesis_pastors)
        )

        print(
            "Genesis members:",
            len(genesis_members)
        )

        if not genesis_pastors:
            raise RuntimeError(
                "No Genesis pastors found"
            )

        if not genesis_members:
            raise RuntimeError(
                "No Genesis members found"
            )

        updated_comments = 0
        reassigned_comments = 0

        for prayer_index, prayer in enumerate(
            prayers
        ):

            comments = (
                db.query(PrayerComment)
                .filter(
                    PrayerComment.prayer_id ==
                        prayer.id,
                    PrayerComment.is_hidden ==
                        False,
                    PrayerComment.comment ==
                        "Praying with you. May God give you peace and strength.",
                )
                .order_by(
                    PrayerComment.created_at.asc(),
                    PrayerComment.id.asc(),
                )
                .all()
            )

            for comment_index, comment in enumerate(
                comments
            ):

                # ---------------------------------
                # Preserve whether the row was
                # originally a pastor response.
                # ---------------------------------

                if comment.is_pastor_response:

                    user = genesis_pastors[
                        (
                            prayer_index +
                            comment_index
                        )
                        % len(genesis_pastors)
                    ]

                    choices = (
                        PASTOR_ENCOURAGEMENTS.get(
                            prayer.category,
                            MEMBER_COMMENTS,
                        )
                    )

                    new_text = choices[
                        (
                            prayer_index +
                            comment_index
                        )
                        % len(choices)
                    ]

                else:

                    user = genesis_members[
                        (
                            prayer_index +
                            comment_index
                        )
                        % len(genesis_members)
                    ]

                    new_text = MEMBER_COMMENTS[
                        (
                            prayer_index +
                            comment_index
                        )
                        % len(MEMBER_COMMENTS)
                    ]

                identity_changed = (
                    comment.user_id != user.id
                    or
                    comment.user_name != user.name
                )

                text_changed = (
                    comment.comment != new_text
                )

                if not (
                    identity_changed
                    or text_changed
                ):
                    continue

                print(
                    f"Prayer {prayer.id} "
                    f"[{prayer.category}]"
                )

                print(
                    "  OLD:",
                    comment.user_name,
                    "|",
                    comment.comment
                )

                print(
                    "  NEW:",
                    user.name,
                    "|",
                    new_text
                )

                print()

                if identity_changed:
                    reassigned_comments += 1

                if text_changed:
                    updated_comments += 1

                if not dry_run:

                    comment.user_id = user.id
                    comment.user_name = user.name
                    comment.comment = new_text

        print(
            "Comments text changed:",
            updated_comments
        )

        print(
            "Comments reassigned to Genesis users:",
            reassigned_comments
        )

        if dry_run:

            db.rollback()

            print("")
            print(
                "✅ DRY RUN COMPLETE — "
                "database not modified"
            )

        else:

            db.commit()

            print("")
            print(
                "✅ Genesis prayer comments "
                "updated successfully"
            )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()
