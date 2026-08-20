from datetime import date, datetime

import pytest

from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.work_center_repository import (
    WorkCenterRepository,
)


@pytest.mark.asyncio
async def test_create_and_get_batch(clean_db):
    work_center_repository = WorkCenterRepository(clean_db)

    work_center = await work_center_repository.create(
        identifier="RC-001",
        name="Цех №1",
    )
    shift_start = datetime.fromisoformat("2026-08-18T08:00:00")
    shift_end = datetime.fromisoformat("2026-08-18T20:00:00")

    repository = BatchRepository(clean_db)

    batch = await repository.create(
        is_closed=False,
        task_description="Изготовить 1000 болтов",
        work_center_id=work_center.id,
        shift="1 смена",
        team="Бригада Иванова",
        batch_number=22222,
        batch_date=date(2026, 8, 18),
        nomenclature="Болт М10",
        ekn_code="EKN-123",
        shift_start=shift_start,
        shift_end=shift_end,
    )

    found = await repository.get_by_id(batch.id)

    assert found is not None
    assert found.batch_number == 22222
