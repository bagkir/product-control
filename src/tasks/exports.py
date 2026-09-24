import asyncio
import os

from celery import Task

from src.celery_app import celery_app
from src.core.celery_database import celery_db_session
from src.data.repositories.batch_repository import BatchRepository
from src.domain.services.batch_export_service import BatchExportService
from src.storage.minio_service import MinIOService
from src.utils.data_parser import _parse_date

EXPORTS_BUCKET = "exports"


@celery_app.task(bind=True, name="tasks.export_batches_to_file", max_retries=3)
def export_batches_to_file(
    self: Task,
    filters: dict,
    format: str = "excel",
) -> dict:
    return asyncio.run(
        _export_batches_to_file_async(
            self,
            filters,
            format,
        )
    )


async def _export_batches_to_file_async(
    task: Task,
    filters: dict,
    format: str,
) -> dict:
    batch_export_service = BatchExportService()
    if format not in {"excel", "csv"}:
        raise ValueError("Format must be 'excel' or 'csv'")

    async with celery_db_session() as session:
        repository = BatchRepository(session)

        batches = await repository.list_for_export(
            is_closed=filters.get("is_closed"),
            batch_number=filters.get("batch_number"),
            date_from=_parse_date(filters.get("date_from")),
            date_to=_parse_date(filters.get("date_to")),
            work_center_id=filters.get("work_center_id"),
            shift=filters.get("shift"),
        )

        task.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": len(batches),
                "progress": 0,
            },
        )

        if format == "excel":
            file_path, file_name = batch_export_service.build_excel(batches)
        else:
            file_path, file_name = batch_export_service.build_csv(batches)

        try:
            storage = MinIOService()

            file_url = await asyncio.to_thread(
                storage.upload_file,
                bucket=EXPORTS_BUCKET,
                file_path=file_path,
                object_name=file_name,
                expires_days=7,
            )

            return {
                "success": True,
                "file_url": file_url,
                "total_batches": len(batches),
            }

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
