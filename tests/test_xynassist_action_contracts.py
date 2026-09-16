from xynassist_service.actions.contracts import (
    get_action_definition,
    is_supported_action,
)


def test_current_xynafaith_actions_are_registered():
    assert is_supported_action(
        "sermon.save",
        product="xynafaith",
    )
    assert is_supported_action(
        "sermon.update",
        product="xynafaith",
    )
    assert is_supported_action(
        "sermon.delete",
        product="xynafaith",
    )


def test_unknown_action_fails_closed():
    assert not is_supported_action(
        "sermon.publish",
        product="xynafaith",
    )


def test_action_is_product_scoped():
    assert not is_supported_action(
        "sermon.save",
        product="xynalegal",
    )


def test_destructive_action_requires_confirmation():
    definition = get_action_definition(
        "sermon.delete"
    )

    assert definition is not None
    assert definition.product == "xynafaith"
    assert definition.confirmation == "required"


def test_non_destructive_action_does_not_require_confirmation():
    definition = get_action_definition(
        "sermon.save"
    )

    assert definition is not None
    assert definition.confirmation == "none"
