import base64
import hmac
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


class PreviewAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/preview-health":
            return await call_next(request)

        username = os.getenv("PREVIEW_USERNAME")
        password = os.getenv("PREVIEW_PASSWORD")

        if not username or not password:
            return JSONResponse(
                {"detail": "Preview access not configured"},
                status_code=503,
            )

        supplied = request.headers.get("authorization", "")

        if supplied.startswith("Basic "):
            try:
                decoded = base64.b64decode(
                    supplied[6:], validate=True
                ).decode("utf-8")

                candidate_user, candidate_password = \
                    decoded.split(":", 1)

                valid_user = hmac.compare_digest(
                    candidate_user, username
                )
                valid_password = hmac.compare_digest(
                    candidate_password, password
                )

                if valid_user and valid_password:
                    return await call_next(request)

            except (ValueError, UnicodeError):
                pass

        return Response(
            status_code=401,
            headers={
                "WWW-Authenticate":
                    'Basic realm="XynaFaith V2 Partner Preview"'
            },
        )


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
