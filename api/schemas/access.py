from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EffectiveAccessResponse(BaseModel):
    """
    Final resolved capability contract.

    The rest of XynaFaith should not care about:
    - subscription tables
    - plans
    - payment providers

    It only consumes this object.
    """

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
