from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AggregateAsyncRequest(BaseModel):
    unique_codes: list[str] = Field(min_length=1, max_length=5000)


class ProductCreate(BaseModel):
    unique_code: str
    batch_id: int


class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_aggregated: bool = False
    aggregated_at: datetime | None
    created_at: datetime


class ProductShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None
