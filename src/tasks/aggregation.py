import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.celery_app import celery_app
from src.core.config import settings
from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.product_repository import ProductRepository

CHUNK_SIZE = 200


@celery_app.task(bind=True, max_retries=3, name="tasks.aggregate_products_batch")
def aggregate_products_batch(
    self,
    batch_id: int,
    unique_codes: list[str],
) -> dict:
    """
    Синхронная точка входа Celery worker'а.

    Каждый вызов задачи создаёт свой event loop через asyncio.run(). Нельзя
    переиспользовать общий module-level engine из src.core.database (тот же,
    что и у FastAPI) — его connection pool привязывается к первому loop'у,
    в котором был использован, и падает с "attached to a different loop"
    на втором вызове задачи. Поэтому здесь — свой engine с NullPool, который
    создаётся и разбирается на каждый запуск задачи.
    """
    return asyncio.run(_aggregate_products_batch_async(self, batch_id, unique_codes))


async def _aggregate_products_batch_async(
    task, batch_id: int, unique_codes: list[str]
) -> dict:
    engine = create_async_engine(str(settings.DATABASE_URL), poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            batch_repository = BatchRepository(session)
            product_repository = ProductRepository(session)

            batch = await batch_repository.get_by_id(batch_id)
            if batch is None:
                raise ValueError(f"Batch {batch_id} not found")

            total = len(unique_codes)
            aggregated_total = 0
            errors: list[dict] = []

            for start in range(0, total, CHUNK_SIZE):
                chunk = unique_codes[start : start + CHUNK_SIZE]

                chunk_result = await product_repository.aggregate_by_codes(
                    batch_id, chunk
                )
                aggregated_total += chunk_result["aggregated"]
                errors.extend(
                    {"code": c, "reason": "already aggregated"}
                    for c in chunk_result["already_aggregated"]
                )
                errors.extend(
                    {"code": c, "reason": "not found in batch"}
                    for c in chunk_result["not_found"]
                )

                await session.commit()

                processed = min(start + CHUNK_SIZE, total)
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": processed,
                        "total": total,
                        "progress": (
                            round(processed / total * 100, 2) if total else 100.0
                        ),
                    },
                )

            return {
                "success": True,
                "total": total,
                "aggregated": aggregated_total,
                "failed": len(errors),
                "errors": errors,
            }
    finally:
        await engine.dispose()
