from api.models.conversation_pending_memory_action import (
    ConversationPendingMemoryAction,
)


def test_pending_memory_action_table_name():
    assert (
        ConversationPendingMemoryAction.__tablename__
        == "conversation_pending_memory_actions"
    )


def test_pending_memory_action_binds_required_state():
    table = ConversationPendingMemoryAction.__table__

    expected = {
        "id",
        "user_id",
        "conversation_id",
        "action_name",
        "memory_type",
        "memory_key",
        "source_message_id",
        "action_request_id",
        "created_at",
    }

    assert set(table.columns.keys()) == expected

    for column_name in (
        "user_id",
        "conversation_id",
        "action_name",
        "memory_type",
        "memory_key",
        "source_message_id",
        "action_request_id",
        "created_at",
    ):
        assert table.columns[column_name].nullable is False


def test_pending_memory_action_is_unique_per_user_conversation():
    table = ConversationPendingMemoryAction.__table__

    constraints = [
        constraint
        for constraint in table.constraints
        if constraint.name
        == (
            "uq_conversation_pending_memory_action_"
            "user_conversation"
        )
    ]

    assert len(constraints) == 1

    columns = {
        column.name
        for column in constraints[0].columns
    }

    assert columns == {
        "user_id",
        "conversation_id",
    }


def test_pending_memory_action_user_fk_cascades():
    table = ConversationPendingMemoryAction.__table__

    foreign_keys = list(
        table.columns.user_id.foreign_keys
    )

    assert len(foreign_keys) == 1

    foreign_key = foreign_keys[0]

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_pending_memory_identity_is_logical_not_internal():
    columns = set(
        ConversationPendingMemoryAction
        .__table__
        .columns
        .keys()
    )

    assert "memory_type" in columns
    assert "memory_key" in columns

    assert "memory_id" not in columns
    assert "xynassist_memory_id" not in columns
    assert "resource_id" not in columns


def test_pending_memory_action_has_stable_execution_identity():
    table = ConversationPendingMemoryAction.__table__

    column = table.columns.action_request_id

    assert column.nullable is False
    assert column.type.length == 36


def test_browser_confirmation_is_not_persisted_as_trust():
    columns = set(
        ConversationPendingMemoryAction
        .__table__
        .columns
        .keys()
    )

    assert "confirmed" not in columns
    assert "trusted_confirmed" not in columns
    assert "confirmation_header" not in columns
