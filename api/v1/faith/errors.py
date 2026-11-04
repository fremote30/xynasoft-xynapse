
from fastapi import Request
from fastapi.responses import JSONResponse

import logging
logger = logging.getLogger("uvicorn.error")

def register_error_handlers(app):
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):
        logger.exception("Unhandled exception: %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "message": "Something went wrong."},
        )
