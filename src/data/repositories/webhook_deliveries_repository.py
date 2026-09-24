from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import (
    WebhookDelivery,
    WebhookSubscription,
)

from .base_repository import BaseRepository


class WebhookDeliveryRepository(BaseRepository[WebhookDelivery]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=WebhookDelivery,
        )

    async def get_by_subscription(
        self,
        subscription_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WebhookDelivery]:
        query = (
            select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_retries(self) -> list[WebhookDelivery]:
        """
        Доставки, готовые к повторной отправке:
        - статус failed или pending
        - attempts < subscription.retry_count
        - прошло достаточно времени с последней попытки (экспоненциальный backoff)
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        MAX_BACKOFF_MINUTES = 60

        stmt = (
            select(WebhookDelivery)
            .join(
                WebhookSubscription,
                WebhookDelivery.subscription_id == WebhookSubscription.id,
            )
            .where(
                WebhookDelivery.status.in_(("failed", "pending")),
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
            )
        )
        result = await self.session.execute(stmt)
        deliveries = list(result.scalars().all())

        ready = []
        for d in deliveries:
            if d.last_attempt_at is None:
                ready.append(d)
                continue

            delay_minutes = min(2**d.attempts, MAX_BACKOFF_MINUTES)
            next_attempt_at = d.last_attempt_at + timedelta(minutes=delay_minutes)
            if now >= next_attempt_at:
                ready.append(d)

        return ready

    async def mark_success(
        self,
        delivery_id: int,
        response_status: int,
        response_body: str | None = None,
    ) -> WebhookDelivery | None:
        return await self.update(
            delivery_id,
            status="success",
            response_status=response_status,
            response_body=response_body,
            delivered_at=datetime.now(UTC).replace(tzinfo=None),
            last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
        )

    async def mark_failed(
        self,
        delivery_id: int,
        error_message: str,
        response_status: int | None = None,
    ) -> WebhookDelivery | None:
        instance = await self.get_by_id(delivery_id)
        if instance is None:
            return None

        return await self.update(
            delivery_id,
            status="failed",
            attempts=instance.attempts + 1,
            error_message=error_message,
            response_status=response_status,
            last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
        )

    async def count_by_subscription(
        self,
        subscription_id: int,
    ) -> int:
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.subscription_id == subscription_id
        )

        return await self.count(stmt)
