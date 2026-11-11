import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "render_preview.py"


def test_preview_auth_switch_exists():
    source = SOURCE.read_text()
    assert 'os.getenv(' in source
    assert '"PREVIEW_AUTH_ENABLED", "true"' in source
    assert 'preview_auth_enabled == "false"' in source


def test_preview_auth_defaults_to_protected():
    source = SOURCE.read_text()
    assert '"PREVIEW_AUTH_ENABLED", "true"' in source
    assert 'if not username or not password or not secret:' in source


def test_preview_auth_syntax():
    ast.parse(SOURCE.read_text())


def test_existing_basic_auth_preserved():
    source = SOURCE.read_text()
    assert 'hmac.compare_digest' in source
    assert 'WWW-Authenticate' in source
    assert 'PREVIEW_COOKIE' in source
