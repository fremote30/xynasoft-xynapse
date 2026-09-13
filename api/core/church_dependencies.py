"""
FastAPI dependencies for XynaFaith V2 Church Space authorization.

Church-scoped authorization is derived from:
1. the authenticated XynaFaith user,
2. the requested Church Space,
3. the user's active ChurchMembership,
4. the permission required by the route.

Legacy User.role does not grant Church Space access.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    ChurchPermissionDenied,
    require_church_permission,
)


def require_church_permission_dependency(
    permission: str,
) -> Callable[..., ChurchMembership]:
    """
    Build a FastAPI dependency for one Church Space permission.

    The route must expose a path/query parameter named ``church_id``.
    The user identity always comes from authentication.
    """

    def dependency(
        church_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> ChurchMembership:
        try:
            return require_church_permission(
                db,
                church_id=church_id,
                user_id=current_user.id,
                permission=permission,
            )

        except ChurchMembershipNotFound as exc:
            # Deliberately avoid revealing whether a foreign Church Space
            # exists to a user who has no membership in it.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Church Space not found",
            ) from exc

        except ChurchMembershipInactive as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Church membership is not active",
            ) from exc

        except ChurchPermissionDenied as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient Church Space permission",
            ) from exc

    return dependency
