import ast
from pathlib import Path


SOURCE = Path("api/routes/users.py")


def get_function():
    tree = ast.parse(SOURCE.read_text())

    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "make_admin"
    ]

    assert len(matches) == 1
    return matches[0]


def test_admin_promotion_requires_authentication():
    node = get_function()

    arguments = {
        arg.arg: default
        for arg, default in zip(
            node.args.args[-len(node.args.defaults):],
            node.args.defaults,
        )
    }

    assert "current_user" in arguments

    assert (
        ast.unparse(arguments["current_user"])
        == "Depends(get_current_user)"
    )


def test_admin_promotion_requires_admin_role():
    node = get_function()
    body = ast.unparse(node)

    assert "current_user.role != 'admin'" in body
    assert "status_code=403" in body
    assert "Admin access required" in body


def test_admin_check_precedes_user_mutation():
    node = get_function()

    body = ast.unparse(node)

    check_position = body.index(
        "current_user.role != 'admin'"
    )

    mutation_position = body.index(
        "user.role = 'admin'"
    )

    assert check_position < mutation_position


def test_admin_promotion_retains_existing_route():
    node = get_function()

    decorators = [
        ast.unparse(item)
        for item in node.decorator_list
    ]

    assert any(
        "'/{user_id}/make-admin'" in item
        for item in decorators
    )
