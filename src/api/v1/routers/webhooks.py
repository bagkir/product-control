from fastapi import APIRouter, status

from src.api.dependencies import ApiKeyDep, WebhookServiceDep
from src.api.v1.schemas.webhook_delivery import WebhookDeliveryListResponse
from src.api.v1.schemas.webhook_subscription import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionListResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"], dependencies=[ApiKeyDep])


@router.post(
    "", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_webhook(
    payload: WebhookSubscriptionCreate,
    service: WebhookServiceDep,
):
    """POST /api/v1/webhooks"""
    return await service.create_subscription(payload)


@router.get("", response_model=WebhookSubscriptionListResponse)
async def list_webhooks(
    service: WebhookServiceDep,
    offset: int = 0,
    limit: int = 20,
):
    """GET /api/v1/webhooks"""
    items, total = await service.list_subscriptions(offset=offset, limit=limit)
    return WebhookSubscriptionListResponse(items=items, total=total)


@router.patch("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    webhook_id: int,
    payload: WebhookSubscriptionUpdate,
    service: WebhookServiceDep,
):
    """PATCH /api/v1/webhooks/{webhook_id}"""
    return await service.update_subscription(webhook_id, payload)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    service: WebhookServiceDep,
):
    """DELETE /api/v1/webhooks/{webhook_id}"""
    await service.delete_subscription(webhook_id)


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: int,
    service: WebhookServiceDep,
    offset: int = 0,
    limit: int = 20,
):
    """GET /api/v1/webhooks/{webhook_id}/deliveries"""
    items, total = await service.list_deliveries(webhook_id, offset=offset, limit=limit)
    return WebhookDeliveryListResponse(items=items, total=total)
