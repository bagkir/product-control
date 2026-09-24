import pytest

from src.data.repositories.webhook_deliveries_repository import (
    WebhookDeliveryRepository,
)
from src.data.repositories.webhook_subscription_repository import (
    WebhookSubscriptionRepository,
)


@pytest.mark.asyncio
async def test_get_pending_retries(clean_db):
    subscription_repository = WebhookSubscriptionRepository(clean_db)

    subscription = await subscription_repository.create(
        url="https://example.com/webhook",
        events=["batch_created"],
        secret_key="secret",
        retry_count=3,
        timeout=10,
        is_active=True,
    )

    delivery_repository = WebhookDeliveryRepository(clean_db)

    delivery = await delivery_repository.create(
        subscription_id=subscription.id,
        event_type="batch_created",
        payload={"event": "batch_created"},
        status="failed",
        attempts=1,
    )

    result = await delivery_repository.get_pending_retries()

    assert len(result) == 1
    assert result[0].id == delivery.id
