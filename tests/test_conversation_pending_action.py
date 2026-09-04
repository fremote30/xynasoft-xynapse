from sqlalchemy import (
    ForeignKeyConstraint,
    UniqueConstraint,
)

from api.models.conversation_pending_action import (
    ConversationPendingAction,
)


def test_pending_action_table_name():
    assert (
        ConversationPendingAction.__tablename__
        == "conversation_pending_actions"
    )


def test_pending_action_binds_required_state():
    table = ConversationPendingAction.__table__

    required_columns = {
        "id",
        "user_id",
        "conversation_id",
        "action_name",
        "resource_type",
        "resource_id",
        "source_message_id",
        "created_at",
    }

    assert set(table.columns.keys()) == required_columns

    for column_name in (
        "user_id",
        "conversation_id",
        "action_name",
        "resource_type",
        "resource_id",
        "source_message_id",
        "created_at",
    ):
        assert table.c[column_name].nullable is False


def test_pending_action_is_unique_per_user_conversation():
    table = ConversationPendingAction.__table__

    constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    ]

    matching = [
        constraint
        for constraint in constraints
        if {
            column.name
            for column in constraint.columns
        }
        == {
            "user_id",
            "conversation_id",
        }
    ]

    assert len(matching) == 1

    assert matching[0].name == (
        "uq_conversation_pending_action_"
        "user_conversation"
    )


def test_pending_action_user_fk_cascades():
    table = ConversationPendingAction.__table__

    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(
            constraint,
            ForeignKeyConstraint,
        )
    ]

    user_fk = next(
        constraint
        for constraint in foreign_keys
        if [
            column.name
            for column in constraint.columns
        ]
        == ["user_id"]
    )

    element = next(iter(user_fk.elements))

    assert (
        element.target_fullname
        == "users.id"
    )
    assert user_fk.ondelete == "CASCADE"


def test_pending_action_resource_is_not_browser_identity():
    """
    The pending-action record contains product-resource
    binding only. It must not contain alternate identity
    fields that could compete with authenticated user_id.
    """

    columns = set(
        ConversationPendingAction.__table__.columns.keys()
    )

    assert "external_user_id" not in columns
    assert "owner_id" not in columns
    assert "email" not in columns
