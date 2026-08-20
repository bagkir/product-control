import json
import logging
import os
import tempfile
import uuid

from fastapi import UploadFile

from src.api.v1.schemas.batch import (
    BatchCreate,
    BatchExportRequest,
    BatchFilter,
    BatchResponse,
    BatchUpdate,
)
from src.api.v1.schemas.report import ReportCreate
from src.api.v1.schemas.task import TaskResponse
from src.core.redis_client import get_redis
from src.data.models import Batch, WorkCenter
from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.work_center_repository import WorkCenterRepository
from src.domain.exceptions.batch_exception import (
    BatchAlreadyExistsException,
    BatchMoreThen100,
    BatchNotFoundException,
)
from src.domain.services.webhook_service import WebhookService
from src.storage.minio_service import MinIOService
from src.tasks.aggregation import aggregate_products_batch
from src.tasks.exports import export_batches_to_file
from src.tasks.imports import import_batches_from_file
from src.tasks.reports import generate_batch_report
from src.utils.cache import cached, invalidate_cache_key, invalidate_cache_pattern
from src.utils.datetime_utils import utc_now_naive

logger = logging.getLogger(__name__)


class BatchService:
    """
    Сервис для работы с партиями.
    """

    def __init__(
        self,
        batch_repository: BatchRepository,
        work_center_repository: WorkCenterRepository,
        webhook_service: WebhookService,
    ):
        self.batch_repository = batch_repository
        self.work_center_repository = work_center_repository
        self.webhook_service = webhook_service

    async def _resolve_work_center(self, data: BatchCreate) -> WorkCenter:
        """
        Найти рабочий центр по ИдентификаторРЦ или создать новый,
        если он ещё не заведён в справочнике.

        Импорт партий (Excel/1С) может приходить с идентификатором РЦ,
        которого ещё нет в базе — создаём его "по факту", а не отклоняем
        всю партию.
        """
        work_center = await self.work_center_repository.get_by_identifier(
            data.work_center_identifier
        )
        if work_center is not None:
            return work_center

        return await self.work_center_repository.create(
            identifier=data.work_center_identifier,
            name=data.work_center,
        )

    async def create_batch(self, data: BatchCreate) -> Batch:
        """Создать одну партию (элемент списка из POST /batches)."""
        if await self.batch_repository.exists_by_number_and_date(
            data.batch_number, data.batch_date
        ):
            raise BatchAlreadyExistsException(data.batch_number, data.batch_date)

        work_center = await self._resolve_work_center(data)

        batch = await self.batch_repository.create(
            is_closed=data.is_closed,
            task_description=data.task_description,
            work_center_id=work_center.id,
            shift=data.shift,
            team=data.team,
            batch_number=data.batch_number,
            batch_date=data.batch_date,
            nomenclature=data.nomenclature,
            ekn_code=data.ekn_code,
            shift_start=data.shift_start,
            shift_end=data.shift_end,
        )
        await self.webhook_service.publish_event(
            event_type="batch_created",
            data={
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_date": batch.batch_date.isoformat(),
                "nomenclature": batch.nomenclature,
                "work_center": work_center.name,
            },
        )
        await invalidate_cache_key("dashboard_stats")
        await invalidate_cache_pattern("batches_list:*")

        return await self.batch_repository.get_by_id_with_products(batch.id)

    async def create_batches(self, items: list[BatchCreate]) -> list[Batch]:
        """
        Создать несколько партий одним запросом (тело POST /batches — массив).

        Каждая партия создаётся отдельным вызовом create_batch — если
        какая-то из них дублируется, упадёт вся операция (сервис не
        решает сам, что коммитить частично — это отдаётся на откуп
        вызывающему коду/транзакции get_db()).
        """
        return [await self.create_batch(item) for item in items]

    async def get_batch(self, batch_id: int) -> dict:
        redis = get_redis()
        key = f"batch_detail:{batch_id}"

        cached_data = await redis.get(key)

        if cached_data is not None:
            return json.loads(cached_data)

        batch = await self.batch_repository.get_by_id_with_products(batch_id)

        if batch is None:
            raise BatchNotFoundException(batch_id)

        result = BatchResponse.model_validate(batch).model_dump(mode="json")

        await redis.setex(
            key,
            600,
            json.dumps(result),
        )

        return result

    async def update_batch(
        self,
        batch_id: int,
        data: BatchUpdate,
    ) -> Batch:
        existing = await self.batch_repository.get_by_id(batch_id)

        if existing is None:
            raise BatchNotFoundException(batch_id)

        was_closed = existing.is_closed

        update_fields = data.model_dump(
            exclude_unset=True,
            by_alias=False,
        )

        old_values = {
            field: getattr(existing, field)
            for field in update_fields
            if hasattr(existing, field)
        }

        will_close = update_fields.get("is_closed") is True and not was_closed

        if "is_closed" in update_fields:
            if update_fields["is_closed"] and not was_closed:
                update_fields["closed_at"] = utc_now_naive()

            elif not update_fields["is_closed"]:
                update_fields["closed_at"] = None

        batch = await self.batch_repository.update(
            batch_id,
            **update_fields,
        )

        changes = {}

        for field, new_value in update_fields.items():
            if field == "closed_at":
                continue

            old_value = old_values.get(field)

            if old_value != new_value:
                changes[field] = new_value

        if changes:
            await self.webhook_service.publish_event(
                event_type="batch_updated",
                data={
                    "id": batch.id,
                    "batch_number": batch.batch_number,
                    "changes": changes,
                },
            )

        if will_close:
            batch = await self.batch_repository.get_by_id_with_products(batch_id)

            total_products = len(batch.products)
            aggregated = sum(1 for product in batch.products if product.is_aggregated)

            aggregation_rate = (
                round(
                    aggregated / total_products * 100,
                    2,
                )
                if total_products
                else 0.0
            )

            await self.webhook_service.publish_event(
                event_type="batch_closed",
                data={
                    "id": batch.id,
                    "batch_number": batch.batch_number,
                    "closed_at": (
                        batch.closed_at.isoformat() if batch.closed_at else None
                    ),
                    "statistics": {
                        "total_products": total_products,
                        "aggregated": aggregated,
                        "aggregation_rate": aggregation_rate,
                    },
                },
            )

        await invalidate_cache_key(f"batch_detail:{batch_id}")
        await invalidate_cache_key(f"batch_statistics:{batch_id}")
        await invalidate_cache_key("dashboard_stats")
        await invalidate_cache_pattern("batches_list:*")

        return await self.batch_repository.get_by_id_with_products(batch_id)

    @cached(ttl=60, key_prefix="batches_list")
    async def list_batches(self, filters: BatchFilter) -> dict:
        batches, total = await self.batch_repository.list_filtered(
            is_closed=filters.is_closed,
            batch_number=filters.batch_number,
            batch_date=filters.batch_date,
            work_center_id=filters.work_center_id,
            shift=filters.shift,
            offset=filters.offset,
            limit=filters.limit,
        )

        return {
            "items": [
                BatchResponse.model_validate(batch).model_dump(mode="json")
                for batch in batches
            ],
            "total": total,
        }

    async def aggregate_batch(self, batch_id: int) -> dict:
        """
        Синхронная агрегация всех продуктов партии (не более 100).
        Возвращает статистику.
        """
        batch = await self.batch_repository.get_by_id_with_products(batch_id)
        if batch is None:
            raise BatchNotFoundException(batch_id)

        total_products = len(batch.products)
        if total_products > 100:
            raise BatchMoreThen100(batch_id=batch_id, count=total_products)

        updated = await self.batch_repository.aggregate_batch(batch_id=batch_id)
        already_aggregated = total_products - updated

        await invalidate_cache_key(f"batch_detail:{batch_id}")
        await invalidate_cache_key(f"batch_statistics:{batch_id}")
        await invalidate_cache_key("dashboard_stats")

        return {
            "status": "success",
            "total_products": total_products,
            "aggregated": updated,
            "already_aggregated": already_aggregated,
        }

    async def start_aggregate_async(
        self, batch_id: int, unique_codes: list[str]
    ) -> "TaskResponse":
        """
        Поставить в очередь массовую агрегацию (>100 единиц) через Celery.

        Импорт celery-задачи делаем внутри метода, а не на уровне модуля —
        чтобы domain-слой не тянул celery_app при обычном импорте сервиса
        (например в юнит-тестах, где Celery/RabbitMQ не подняты).
        """

        batch = await self.batch_repository.get_by_id(batch_id)
        if batch is None:
            raise BatchNotFoundException(batch_id)

        task = aggregate_products_batch.delay(
            batch_id=batch_id,
            unique_codes=unique_codes,
        )

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message="Aggregation task started",
        )

    async def start_generate_report(
        self, batch_id: int, data: "ReportCreate"
    ) -> "TaskResponse":
        batch = await self.batch_repository.get_by_id(batch_id)
        if batch is None:
            raise BatchNotFoundException(batch_id)

        task = generate_batch_report.delay(
            batch_id=batch_id,
            format=data.format,
            user_email=data.email,
        )

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message="Report generation started",
        )

    async def start_import(self, file: UploadFile) -> "TaskResponse":
        """
        Загрузить файл в MinIO и запустить Celery-задачу импорта.
        """
        # Проверка расширения
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".xlsx", ".csv"):
            raise ValueError("Only .xlsx or .csv files are supported")

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            storage = MinIOService()
            object_name = f"imports/{uuid.uuid4()}{ext}"
            # Получаем pre-signed URL для скачивания (задача скачает файл по этому URL)
            file_url = storage.upload_file(
                bucket="imports",
                file_path=tmp_path,
                object_name=object_name,
                expires_days=1,  # достаточно на время выполнения задачи
            )
        finally:
            os.unlink(tmp_path)  # удаляем временный файл

        # Запускаем Celery-задачу
        task = import_batches_from_file.delay(file_url=file_url, user_id=None)
        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message="Import task started",
        )

    async def start_export(self, payload: BatchExportRequest) -> "TaskResponse":
        """
        Запустить Celery-задачу экспорта.
        """
        task = export_batches_to_file.delay(
            filters=payload.filters.model_dump(mode="json", exclude_unset=True),
            format=payload.format,
        )
        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message="Export task started",
        )
