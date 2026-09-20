"""
Standalone XynAssist application.

Run locally with:

    uvicorn xynassist_service.main:app \
        --host 0.0.0.0 \
        --port 8001
"""

from fastapi import FastAPI

from xynassist_service.routes.health import (
    router as health_router,
)
from xynassist_service.routes.xynafaith_conversations import (
    router as xynafaith_conversations_router,
)
from xynassist_service.routes.xynafaith_memories import (
    router as xynafaith_memories_router,
)
from xynassist_service.routes.xynafaith_memory_actions import (
    router as xynafaith_memory_actions_router,
)
from xynassist_service.routes.xynafaith_ministry import (
    router as xynafaith_ministry_router,
)


app = FastAPI(
    title="XynAssist API",
    version="2.0.0",
)

app.include_router(health_router)
app.include_router(
    xynafaith_conversations_router
)
app.include_router(
    xynafaith_memories_router
)
app.include_router(
    xynafaith_memory_actions_router
)
app.include_router(
    xynafaith_ministry_router
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "XynAssist",
        "status": "running",
    }
