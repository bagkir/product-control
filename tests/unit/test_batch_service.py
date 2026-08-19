from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.v1.schemas.batch import BatchUpdate
from src.domain.exceptions.batch_exception import (
    BatchAlreadyExistsException,
    BatchNotFoundException,
)
from src.domain.services.batch_service import BatchService


def make_batch_create():
    data = MagicMock()

    data.is_closed = False
    data.task_description = "Изготовить 1000 болтов"
    data.work_center_identifier = "RC-001"
    data.work_center = "Цех №1"
    data.shift = "1 смена"
    data.team = "Бригада Иванова"
    data.batch_number = 22222
    data.batch_date = date(2026, 8, 18)
    data.nomenclature = "Болт М10"
    data.ekn_code = "EKN-123"
    data.shift_start = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)
    data.shift_end = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)

    return data


def _patch_cache(monkeypatch):
    """
    create_batch/update_batch реально дергают invalidate_cache_key /
    invalidate_cache_pattern из src.utils.cache, которые внутри лезут
    в настоящий Redis (get_redis()). Это юнит-тесты сервисного слоя на
    моках репозиториев — без этого патча они тихо превращаются в
    интеграционные тесты, зависящие от поднятого Redis, и падают/висят
    вне docker-сети, где хост "redis" не резолвится.
    """
    monkeypatch.setattr(
        "src.domain.services.batch_service.invalidate_cache_key",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "src.domain.services.batch_service.invalidate_cache_pattern",
        AsyncMock(),
    )


@pytest.mark.asyncio
async def test_create_batch_success(monkeypatch):
    _patch_cache(monkeypatch)

    batch_repository = MagicMock()
    work_center_repository = MagicMock()
    webhook_service = MagicMock()

    batch_repository.exists_by_number_and_date = AsyncMock(return_value=False)

    work_center = MagicMock()
    work_center.id = 1
    work_center.name = "Цех №1"

    work_center_repository.get_by_identifier = AsyncMock(return_value=work_center)

    created_batch = MagicMock()
    created_batch.id = 10
    created_batch.batch_number = 22222
    created_batch.batch_date = date(2026, 8, 18)
    created_batch.nomenclature = "Болт М10"

    batch_repository.create = AsyncMock(return_value=created_batch)

    batch_repository.get_by_id_with_products = AsyncMock(return_value=created_batch)

    webhook_service.publish_event = AsyncMock()

    service = BatchService(
        batch_repository=batch_repository,
        work_center_repository=work_center_repository,
        webhook_service=webhook_service,
    )

    result = await service.create_batch(make_batch_create())

    assert result == created_batch

    batch_repository.create.assert_awaited_once()
    webhook_service.publish_event.assert_awaited_once()

    event = webhook_service.publish_event.await_args.kwargs

    assert event["event_type"] == "batch_created"
    assert event["data"]["id"] == 10


@pytest.mark.asyncio
async def test_create_batch_duplicate():
    batch_repository = MagicMock()
    work_center_repository = MagicMock()
    webhook_service = MagicMock()

    batch_repository.exists_by_number_and_date = AsyncMock(return_value=True)

    service = BatchService(
        batch_repository=batch_repository,
        work_center_repository=work_center_repository,
        webhook_service=webhook_service,
    )

    with pytest.raises(BatchAlreadyExistsException):
        await service.create_batch(make_batch_create())

    work_center_repository.create.assert_not_called()
    batch_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_update_batch_not_found():
    batch_repository = MagicMock()
    work_center_repository = MagicMock()
    webhook_service = MagicMock()

    batch_repository.get_by_id = AsyncMock(return_value=None)

    service = BatchService(
        batch_repository=batch_repository,
        work_center_repository=work_center_repository,
        webhook_service=webhook_service,
    )

    update_data = MagicMock()

    with pytest.raises(BatchNotFoundException):
        await service.update_batch(
            batch_id=999,
            data=update_data,
        )


@pytest.mark.asyncio
async def test_update_batch_closing_publishes_both_events(monkeypatch):
    """
    Закрытие партии (is_closed: false -> true) должно опубликовать ДВА
    события: batch_updated (т.к. is_closed реально изменился) и batch_closed
    (т.к. это переход в закрытое состояние) — со статистикой по продукции.
    """
    _patch_cache(monkeypatch)

    batch_repository = MagicMock()
    work_center_repository = MagicMock()
    webhook_service = MagicMock()

    existing = MagicMock()
    existing.is_closed = False
    batch_repository.get_by_id = AsyncMock(return_value=existing)
    batch_repository.update = AsyncMock()

    closed_batch = MagicMock()
    closed_batch.id = 10
    closed_batch.batch_number = 22222
    closed_batch.closed_at = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    closed_batch.products = [
        MagicMock(is_aggregated=True),
        MagicMock(is_aggregated=False),
    ]
    batch_repository.get_by_id_with_products = AsyncMock(return_value=closed_batch)

    webhook_service.publish_event = AsyncMock()

    service = BatchService(
        batch_repository=batch_repository,
        work_center_repository=work_center_repository,
        webhook_service=webhook_service,
    )

    result = await service.update_batch(
        batch_id=10,
        data=BatchUpdate(is_closed=True),
    )

    assert result == closed_batch
    assert webhook_service.publish_event.await_count == 2

    events = {
        call.kwargs["event_type"]: call.kwargs
        for call in webhook_service.publish_event.await_args_list
    }

    assert set(events.keys()) == {"batch_updated", "batch_closed"}
    assert events["batch_updated"]["data"]["changes"] == {"is_closed": True}

    stats = events["batch_closed"]["data"]["statistics"]
    assert stats["total_products"] == 2
    assert stats["aggregated"] == 1
    assert stats["aggregation_rate"] == 50.0
