import asyncio
import json
import logging

import httpx

from src.celery_app import celery_app
from src.core.celery_database import celery_db_session
from src.data.repositories import (
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)
from src.utils.hmac_utils import generate_signature

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.send_webhook_delivery",
)
def send_webhook_delivery(
    delivery_id: int,
) -> dict:
    return asyncio.run(_send_webhook_delivery_async(delivery_id))


async def _send_webhook_delivery_async(
    delivery_id: int,
) -> dict:
    async with celery_db_session() as session:
        delivery_repository = WebhookDeliveryRepository(session)
        subscription_repository = WebhookSubscriptionRepository(session)

        delivery = await delivery_repository.get_by_id(delivery_id)

        if delivery is None:
            return {
                "success": False,
                "reason": "delivery_not_found",
            }

        if delivery.status == "success":
            return {
                "success": True,
                "status": "already_delivered",
            }

        subscription = await subscription_repository.get_by_id(delivery.subscription_id)

        if subscription is None:
            await delivery_repository.mark_failed(
                delivery_id=delivery_id,
                error_message="Webhook subscription not found",
            )
            await session.commit()

            return {
                "success": False,
                "reason": "subscription_not_found",
            }

        if not subscription.is_active:
            await delivery_repository.mark_failed(
                delivery_id=delivery_id,
                error_message="Webhook subscription is inactive",
            )
            await session.commit()

            return {
                "success": False,
                "reason": "subscription_inactive",
            }

        body = json.dumps(
            delivery.payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        signature = generate_signature(
            payload=body,
            secret_key=subscription.secret_key,
        )

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        }

        try:
            async with httpx.AsyncClient(timeout=subscription.timeout) as client:
                response = await client.post(
                    subscription.url,
                    content=body,
                    headers=headers,
                )

            if 200 <= response.status_code < 300:
                await delivery_repository.mark_success(
                    delivery_id=delivery_id,
                    response_status=response.status_code,
                    response_body=response.text[:4000],
                )

                await session.commit()

                return {
                    "success": True,
                    "status": "delivered",
                    "response_status": response.status_code,
                }

            await delivery_repository.mark_failed(
                delivery_id=delivery_id,
                error_message=(f"HTTP {response.status_code}: {response.text[:1000]}"),
                response_status=response.status_code,
            )

            await session.commit()

            return {
                "success": False,
                "status": "failed",
                "response_status": response.status_code,
            }

        except httpx.HTTPError as exc:
            await delivery_repository.mark_failed(
                delivery_id=delivery_id,
                error_message=str(exc),
            )

            await session.commit()

            logger.exception(
                "Webhook delivery failed: delivery_id=%s",
                delivery_id,
            )

            return {
                "success": False,
                "status": "failed",
                "error": str(exc),
            }


@celery_app.task(
    name="tasks.retry_failed_webhooks",
)
def retry_failed_webhooks() -> dict:
    return asyncio.run(_retry_failed_webhooks_async())


async def _retry_failed_webhooks_async() -> dict:
    async with celery_db_session() as session:
        repository = WebhookDeliveryRepository(session)

        deliveries = await repository.get_pending_retries()

        for delivery in deliveries:
            send_webhook_delivery.delay(delivery.id)

        return {
            "success": True,
            "scheduled": len(deliveries),
        }
