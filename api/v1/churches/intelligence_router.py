"""XynaFaith V2 Church Intelligence API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import PERMISSION_ANALYTICS_VIEW
from api.core.dependencies import get_current_user
from api.core.entitlements import ENTITLEMENT_CHURCH_INTELLIGENCE
from api.db.database import get_db
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.services.church_intelligence_service import (
    get_church_intelligence_summary,
)
from api.services.effective_access_service import has_entitlement


router = APIRouter()

analytics_view_required = require_church_permission_dependency(
    PERMISSION_ANALYTICS_VIEW
)


def _require_church_intelligence_entitlement(
    db: Session,
    *,
    user: User,
    church_id: int,
) -> None:
    if not has_entitlement(
        db,
        user,
        ENTITLEMENT_CHURCH_INTELLIGENCE,
        church_id=church_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Church Intelligence is not available",
        )


@router.get("/{church_id}/intelligence/summary")
def church_intelligence_summary(
    church_id: int,
    _: ChurchMembership = Depends(analytics_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return deterministic operational intelligence for one Church Space."""

    _require_church_intelligence_entitlement(
        db,
        user=current_user,
        church_id=church_id,
    )

    return get_church_intelligence_summary(
        db,
        church_id=church_id,
    )
