from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WebhookEvent = Literal[
    "batch_created",
    "batch_updated",
    "batch_closed",
    "product_aggregated",
    "report_generated",
    "import_completed",
]


class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: list[WebhookEvent]
    secret_key: str
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=10, ge=1, le=60)


class WebhookSubscriptionUpdate(BaseModel):
    url: str | None = None
    events: list[WebhookEvent] | None = None
    secret_key: str | None = None
    is_active: bool | None = None
    retry_count: int | None = Field(
        default=None,
        ge=0,
        le=10,
    )
    timeout: int | None = Field(
        default=None,
        ge=1,
        le=60,
    )


class WebhookSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    events: list[WebhookEvent]
    is_active: bool
    retry_count: int
    timeout: int
    created_at: datetime
    updated_at: datetime


class WebhookSubscriptionListResponse(BaseModel):
    items: list[WebhookSubscriptionResponse]
    total: int
