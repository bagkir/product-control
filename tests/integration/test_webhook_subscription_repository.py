import pytest

from src.data.repositories.webhook_subscription_repository import (
    WebhookSubscriptionRepository,
)


@pytest.mark.asyncio
async def test_get_active_for_event(clean_db):
    repository = WebhookSubscriptionRepository(clean_db)

    active = await repository.create(
        url="https://example.com/webhook",
        events=[
            "batch_created",
            "batch_closed",
        ],
        secret_key="secret",
        retry_count=3,
        timeout=10,
        is_active=True,
    )

    _inactive = await repository.create(
        url="https://example.com/inactive",
        events=["batch_created"],
        secret_key="secret",
        retry_count=3,
        timeout=10,
        is_active=False,
    )

    result = await repository.get_active_for_event("batch_created")

    assert len(result) == 1
    assert result[0].id == active.id
