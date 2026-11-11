import ast
from pathlib import Path


def test_dashboard_prayer_endpoints_require_authentication():
    tree = ast.parse(
        Path("api/routes/prayer_routes.py").read_text()
    )

    for name in ("recent_prayers", "member_prayers"):
        functions = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == name
        ]

        assert len(functions) == 1

        function = functions[0]
        signature = ast.unparse(function.args)

        assert "Depends(get_current_user)" in signature


def test_dashboard_prayer_visibility_filters_preserved():
    tree = ast.parse(
        Path("api/routes/prayer_routes.py").read_text()
    )

    for name in ("recent_prayers", "member_prayers"):
        function = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == name
        )

        body = ast.unparse(function)

        assert "Prayer.is_hidden == False" in body
        assert "community" in body
        assert "mixed" in body
