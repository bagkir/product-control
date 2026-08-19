from datetime import UTC, datetime
from typing import Any

from src.api.v1.schemas.webhook_subscription import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
)
from src.data.repositories.webhook_deliveries_repository import (
    WebhookDeliveryRepository,
)
from src.data.repositories.webhook_subscription_repository import (
    WebhookSubscriptionRepository,
)
from src.domain.exceptions.webhook_exception import (
    WebhookSubscriptionNotFoundException,
)
from src.tasks.webhooks import send_webhook_delivery


class WebhookService:
    """
    CRUD webhook-подписок и публикация событий.

    Отправку HTTP webhook выполняет Celery.
    """

    def __init__(
        self,
        subscription_repository: WebhookSubscriptionRepository,
        delivery_repository: WebhookDeliveryRepository,
    ):
        self.subscription_repository = subscription_repository
        self.delivery_repository = delivery_repository

    async def create_subscription(
        self,
        data: WebhookSubscriptionCreate,
    ):
        return await self.subscription_repository.create(
            url=data.url,
            events=data.events,
            secret_key=data.secret_key,
            retry_count=data.retry_count,
            timeout=data.timeout,
        )

    async def get_subscription(
        self,
        subscription_id: int,
    ):
        subscription = await self.subscription_repository.get_by_id(subscription_id)

        if subscription is None:
            raise WebhookSubscriptionNotFoundException(subscription_id)

        return subscription

    async def list_subscriptions(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        items = await self.subscription_repository.get_all(
            limit=limit,
            offset=offset,
        )
        total = await self.subscription_repository.count()

        return items, total

    async def update_subscription(
        self,
        subscription_id: int,
        data: WebhookSubscriptionUpdate,
    ):
        await self.get_subscription(subscription_id)

        update_fields = data.model_dump(exclude_unset=True)

        return await self.subscription_repository.update(
            subscription_id,
            **update_fields,
        )

    async def delete_subscription(
        self,
        subscription_id: int,
    ) -> None:
        await self.get_subscription(subscription_id)

        await self.subscription_repository.delete(subscription_id)

    async def list_deliveries(
        self,
        subscription_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        await self.get_subscription(subscription_id)

        items = await self.delivery_repository.get_by_subscription(
            subscription_id,
            limit=limit,
            offset=offset,
        )

        total = await self.delivery_repository.count_by_subscription(subscription_id)

        return items, total

    async def publish_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Создает WebhookDelivery для каждой активной подписки
        и ставит доставку в Celery.
        """

        subscriptions = await self.subscription_repository.get_active_for_event(
            event_type
        )

        if not subscriptions:
            return 0

        payload = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        delivery_ids: list[int] = []

        for subscription in subscriptions:
            delivery = await self.delivery_repository.create(
                subscription_id=subscription.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempts=0,
            )

            delivery_ids.append(delivery.id)

        await self.delivery_repository.session.commit()

        for delivery_id in delivery_ids:
            send_webhook_delivery.delay(delivery_id)

        return len(delivery_ids)
