import asyncio
import importlib
import os
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response


def run_request(path="/", headers=None):
    from preview_middleware_test_loader import PreviewAccessMiddleware

    middleware = PreviewAccessMiddleware(
        app=lambda scope, receive, send: None
    )

    async def receive():
        return {"type": "http.request", "body": b""}

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "scheme": "https",
        "query_string": b"",
        "headers": [
            (k.lower().encode(), v.encode())
            for k, v in (headers or {}).items()
        ],
        "server": ("localhost", 443),
        "client": ("127.0.0.1", 12345),
        "http_version": "1.1",
    }

    request = Request(scope, receive)

    async def next_handler(request):
        return Response("PUBLIC_HOME", status_code=200)

    return asyncio.run(
        middleware.dispatch(request, next_handler)
    )


def test_missing_credentials_fail_closed():
    with patch.dict(os.environ, {
        "PREVIEW_AUTH_ENABLED": "true",
        "PREVIEW_USERNAME": "",
        "PREVIEW_PASSWORD": "",
        "SECRET_KEY": "test-secret",
    }):
        response = run_request()
        assert response.status_code == 503


def test_enabled_preview_requires_basic_auth():
    with patch.dict(os.environ, {
        "PREVIEW_AUTH_ENABLED": "true",
        "PREVIEW_USERNAME": "tester",
        "PREVIEW_PASSWORD": "test-password",
        "SECRET_KEY": "test-secret",
    }):
        response = run_request()
        assert response.status_code == 401
        assert "Basic" in response.headers["WWW-Authenticate"]


def test_disabled_preview_allows_public_home():
    with patch.dict(os.environ, {
        "PREVIEW_AUTH_ENABLED": "false",
        "PREVIEW_USERNAME": "",
        "PREVIEW_PASSWORD": "",
        "SECRET_KEY": "test-secret",
    }):
        response = run_request()
        assert response.status_code == 200
        assert response.body == b"PUBLIC_HOME"


def test_invalid_setting_fails_closed():
    with patch.dict(os.environ, {
        "PREVIEW_AUTH_ENABLED": "unexpected",
        "PREVIEW_USERNAME": "",
        "PREVIEW_PASSWORD": "",
        "SECRET_KEY": "test-secret",
    }):
        response = run_request()
        assert response.status_code == 503
