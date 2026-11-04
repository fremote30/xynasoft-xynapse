from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EffectiveAccessResponse(BaseModel):

    user_id: int

    role: str

    access_profile: str

    plan_code: Optional[str] = None

    entitlements: List[str] = Field(
        default_factory=list
    )

    limits: Dict[str, int] = Field(
        default_factory=dict
    )

    source_profile: str



class FeatureGateResponse(BaseModel):
    """
    Result of feature authorization.
    """

    allowed: bool

    entitlement_key: str

    reason: str

    access_profile: str

    plan_code: Optional[str] = None


class UsageVisibilityResponse(BaseModel):
    entitlement_key: str
    metric: str
    quota_scope: str
    allowance_units: int
    consumed_units: int
    reserved_units: int
    available_units: int
    period_start: datetime
    period_end: datetime
