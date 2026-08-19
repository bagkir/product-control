from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorkCenterCreate(BaseModel):
    identifier: str
    name: str


class WorkCenterUpdate(BaseModel):
    identifier: str | None = None
    name: str | None = None


class WorkCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identifier: str
    name: str
    created_at: datetime
    updated_at: datetime
