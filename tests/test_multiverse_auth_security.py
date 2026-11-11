import ast
from pathlib import Path


def test_multiverse_requires_authenticated_user():
    tree = ast.parse(
        Path("api/routes/faith.py").read_text()
    )

    matches = [
        n for n in tree.body
        if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and n.name == "multiverse_sermons"
    ]

    assert len(matches) == 1

    node = matches[0]

    assert any(
        arg.arg == "current_user"
        for arg in node.args.args
    )

    assert "Depends(get_current_user)" in ast.unparse(node)
