from datetime import UTC, datetime

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
        Доставки, которым стоит попробовать отправиться снова:
        - status == "failed" и попыток ещё не исчерпано (< subscription.retry_count)
        - ИЛИ status == "pending" — подстраховка на случай, если исходный
          send_webhook_delivery.delay() был вызван ДО commit транзакции,
          создавшей эту запись, и воркер не нашёл строку по id
          (см. race condition ниже). Раз в 15 минут подбираем то, что
          могло "потеряться" в этом окне.
        """
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
        return list(result.scalars().all())

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
        )

    async def count_by_subscription(
        self,
        subscription_id: int,
    ) -> int:
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.subscription_id == subscription_id
        )

        return await self.count(stmt)
