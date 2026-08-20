import ipaddress
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

WebhookEvent = Literal[
    "batch_created",
    "batch_updated",
    "batch_closed",
    "product_aggregated",
    "report_generated",
    "import_completed",
]

_BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0", "0"}


def _validate_webhook_url(url: str) -> str:
    """
    Базовая защита от SSRF: только http/https и запрет literal-IP из
    приватных/loopback/link-local диапазонов.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Webhook URL must use http or https scheme")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Webhook URL must include a hostname")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError("Webhook URL host is not allowed")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return url

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    ):
        raise ValueError("Webhook URL must not point to a private/internal address")

    return url


class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: list[WebhookEvent]
    secret_key: str
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=10, ge=1, le=60)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _validate_webhook_url(value)


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

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_webhook_url(value)


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
