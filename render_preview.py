import base64
import hmac
import hashlib
import time
import os
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from main import app

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "ui-faith-v2-unified"

if not (FRONTEND / "index.html").is_file():
    raise RuntimeError("Unified V2 frontend missing")



PREVIEW_COOKIE = "xynafaith_v2_preview_session"
PREVIEW_SESSION_SECONDS = 3600


def _preview_signature(timestamp, username, password):
    secret = os.getenv("SECRET_KEY")

    if not secret:
        return None

    key = hashlib.sha256(
        (
            secret + chr(0) +
            username + chr(0) +
            password
        ).encode("utf-8")
    ).digest()

    return hmac.new(
        key,
        timestamp.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _valid_preview_cookie(value, username, password):
    if not value or len(value) > 128:
        return False

    try:
        timestamp, signature = value.split(".", 1)

        if not timestamp.isascii() or not timestamp.isdecimal():
            return False

        issued = int(timestamp)
        now = int(time.time())

        if issued > now or now - issued >= PREVIEW_SESSION_SECONDS:
            return False

        expected = _preview_signature(
            timestamp, username, password
        )

        return bool(expected) and hmac.compare_digest(
            signature, expected
        )

    except (ValueError, OverflowError):
        return False


class PreviewAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/preview-health":
            return await call_next(request)

        username = os.getenv("PREVIEW_USERNAME")
        password = os.getenv("PREVIEW_PASSWORD")
        secret = os.getenv("SECRET_KEY")

        if not username or not password or not secret:
            return JSONResponse(
                {"detail": "Preview access not configured"},
                status_code=503,
            )

        supplied = request.headers.get("authorization", "")
        valid_basic = False

        if supplied.startswith("Basic "):
            try:
                decoded = base64.b64decode(
                    supplied[6:], validate=True
                ).decode("utf-8")

                candidate_user, candidate_password = (
                    decoded.split(":", 1)
                )

                valid_basic = (
                    hmac.compare_digest(candidate_user, username)
                    and hmac.compare_digest(
                        candidate_password, password
                    )
                )

            except (ValueError, UnicodeError):
                pass

        valid_cookie = _valid_preview_cookie(
            request.cookies.get(PREVIEW_COOKIE),
            username,
            password,
        )

        if not valid_basic and not valid_cookie:
            return Response(
                status_code=401,
                headers={
                    "WWW-Authenticate":
                        'Basic realm="XynaFaith V2 Partner Preview"'
                },
            )

        response = await call_next(request)

        if valid_basic:
            timestamp = str(int(time.time()))
            signature = _preview_signature(
                timestamp, username, password
            )

            response.set_cookie(
                key=PREVIEW_COOKIE,
                value=f"{timestamp}.{signature}",
                max_age=PREVIEW_SESSION_SECONDS,
                httponly=True,
                secure=True,
                samesite="lax",
                path="/",
            )

        return response


app.add_middleware(PreviewAccessMiddleware)


@app.get("/preview-health", include_in_schema=False)
def preview_health():
    return {
        "status": "ok",
        "service": "xynafaith-v2-preview",
    }


# Serve the absolute asset URLs used by the V2 SPA.
# This must precede the root static mount.
app.mount(
    "/ui-faith-v2-unified",
    StaticFiles(directory=str(FRONTEND), html=True),
    name="unified-v2-assets",
)

app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND), html=True),
    name="unified-v2-preview",
)
