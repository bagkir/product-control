from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.webhook_service import WebhookService


@pytest.mark.asyncio
async def test_publish_event_creates_deliveries(monkeypatch):
    delay_mock = MagicMock()
    monkeypatch.setattr(
        "src.domain.services.webhook_service.send_webhook_delivery.delay",
        delay_mock,
    )

    subscription_repository = MagicMock()
    delivery_repository = MagicMock()

    subscription_repository.get_active_for_event = AsyncMock(
        return_value=[
            MagicMock(id=1),
            MagicMock(id=2),
        ]
    )

    delivery_repository.create = AsyncMock(
        side_effect=[
            MagicMock(id=100),
            MagicMock(id=101),
        ]
    )

    delivery_repository.session = MagicMock()
    delivery_repository.session.commit = AsyncMock()

    service = WebhookService(
        subscription_repository=subscription_repository,
        delivery_repository=delivery_repository,
    )

    result = await service.publish_event(
        event_type="batch_created",
        data={
            "id": 1,
            "batch_number": 22222,
        },
    )

    assert result == 2

    assert delivery_repository.create.await_count == 2

    delivery_repository.session.commit.assert_awaited_once()

    assert delay_mock.call_count == 2
    delay_mock.assert_any_call(100)
    delay_mock.assert_any_call(101)


@pytest.mark.asyncio
async def test_publish_event_without_subscriptions():
    subscription_repository = MagicMock()
    delivery_repository = MagicMock()

    subscription_repository.get_active_for_event = AsyncMock(return_value=[])

    service = WebhookService(
        subscription_repository=subscription_repository,
        delivery_repository=delivery_repository,
    )

    result = await service.publish_event(
        event_type="batch_created",
        data={},
    )

    assert result == 0
    delivery_repository.create.assert_not_called()
