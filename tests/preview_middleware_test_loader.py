"""Load the real preview middleware without importing the full app."""

import ast
import base64
import hashlib
import hmac
import os
import time
from pathlib import Path

from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "render_preview.py"
)

tree = ast.parse(SOURCE.read_text())

wanted = {
    "_preview_signature",
    "_valid_preview_cookie",
    "PreviewAccessMiddleware",
}

selected = [
    node
    for node in tree.body
    if (
        isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and node.name in wanted
    )
]

assert len(selected) == 3, (
    "Expected preview middleware definitions not found"
)

module = ast.Module(body=selected, type_ignores=[])

namespace = {
    "base64": base64,
    "hashlib": hashlib,
    "hmac": hmac,
    "os": os,
    "time": time,
    "JSONResponse": JSONResponse,
    "Response": Response,
    "BaseHTTPMiddleware": BaseHTTPMiddleware,
    "Request": Request,
    "PREVIEW_COOKIE": "xynafaith_v2_preview_session",
    "PREVIEW_SESSION_SECONDS": 3600,
}

exec(compile(module, str(SOURCE), "exec"), namespace)

PreviewAccessMiddleware = namespace[
    "PreviewAccessMiddleware"
]
