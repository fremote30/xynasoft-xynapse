from pydantic import BaseModel, ConfigDict, Field


class ChurchGroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    group_type: str


class ChurchGroupMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    church_membership_id: int = Field(gt=0)
    role: str



class ChurchGroupMemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = None
    status: str | None = None
