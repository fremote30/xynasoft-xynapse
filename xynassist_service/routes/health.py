"""
Operational health endpoints for XynAssist.
"""

from fastapi import APIRouter


router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "xynassist",
    }
