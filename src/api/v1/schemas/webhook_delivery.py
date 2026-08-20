from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.api.v1.schemas.webhook_subscription import WebhookEvent

WebhookDeliveryStatus = Literal[
    "pending",
    "success",
    "failed",
]


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    event_type: WebhookEvent
    status: WebhookDeliveryStatus
    attempts: int
    response_status: int | None
    response_body: str | None
    error_message: str | None
    created_at: datetime
    delivered_at: datetime | None


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryResponse]
    total: int
