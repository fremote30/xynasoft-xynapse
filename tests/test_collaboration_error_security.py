import ast
from pathlib import Path


def test_collaboration_does_not_expose_exception_text():
    source = Path(
        "api/routes/collaboration_routes.py"
    ).read_text()

    tree = ast.parse(source)

    assert "detail=str(e)" not in source
    assert "Unable to share sermon" in source

    assert tree is not None
