from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import WebhookSubscription

from .base_repository import BaseRepository


class WebhookSubscriptionRepository(BaseRepository[WebhookSubscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=WebhookSubscription)

    async def get_active_for_event(self, event_type: str) -> list[WebhookSubscription]:
        """
        Активные подписки, которые подписаны на данный тип события.

        Используется перед постановкой в очередь WebhookDelivery для
        конкретного события (batch_created, product_aggregated и т.д.).
        """
        query = select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def deactivate(self, subscription_id: int) -> WebhookSubscription | None:
        """Мягкое отключение подписки (is_active = False)."""
        return await self.update(subscription_id, is_active=False)
