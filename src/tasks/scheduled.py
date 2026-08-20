import asyncio
import json
from datetime import UTC, datetime, timedelta

from src.celery_app import celery_app
from src.core.celery_database import celery_db_session
from src.core.redis_client import celery_redis_client
from src.data.repositories import (
    AnalyticsRepository,
    BatchRepository,
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)
from src.domain.services.webhook_service import WebhookService
from src.storage.minio_service import MinIOService
from src.utils.cache import invalidate_cache_key, invalidate_cache_pattern
from src.utils.datetime_utils import utc_now_naive

FILE_BUCKETS = (
    "reports",
    "exports",
    "imports",
)


@celery_app.task(name="tasks.auto_close_expired_batches")
def auto_close_expired_batches() -> dict:
    return asyncio.run(_auto_close_expired_batches_async())


async def _auto_close_expired_batches_async() -> dict:
    now = utc_now_naive()

    async with celery_db_session() as session:
        repository = BatchRepository(session)
        webhook_service = WebhookService(
            subscription_repository=WebhookSubscriptionRepository(session),
            delivery_repository=WebhookDeliveryRepository(session),
        )

        closed_batches = await repository.close_expired(now)

        if closed_batches:
            async with celery_redis_client() as redis_client:
                for batch in closed_batches:
                    total = len(batch.products)
                    aggregated = sum(1 for p in batch.products if p.is_aggregated)
                    rate = round(aggregated / total * 100, 2) if total else 0.0

                    await webhook_service.publish_event(
                        event_type="batch_closed",
                        data={
                            "id": batch.id,
                            "batch_number": batch.batch_number,
                            "closed_at": batch.closed_at.isoformat(),
                            "statistics": {
                                "total_products": total,
                                "aggregated": aggregated,
                                "aggregation_rate": rate,
                            },
                        },
                    )
                    await invalidate_cache_key(
                        f"batch_detail:{batch.id}", client=redis_client
                    )
                    await invalidate_cache_key(
                        f"batch_statistics:{batch.id}", client=redis_client
                    )

                await invalidate_cache_pattern("batches_list:*", client=redis_client)
                await invalidate_cache_key("dashboard_stats", client=redis_client)

        await session.commit()

        return {
            "success": True,
            "closed_count": len(closed_batches),
            "closed_at": now.isoformat(),
        }


@celery_app.task(name="tasks.cleanup_old_files")
def cleanup_old_files() -> dict:
    return asyncio.run(_cleanup_old_files_async())


async def _cleanup_old_files_async() -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=30)

    storage = MinIOService()
    deleted = 0

    for bucket in FILE_BUCKETS:
        for obj in storage.list_files(bucket):
            if obj.last_modified < cutoff:
                storage.delete_file(
                    bucket=bucket,
                    object_name=obj.object_name,
                )
                deleted += 1

    return {
        "success": True,
        "deleted_files": deleted,
    }


@celery_app.task(name="tasks.update_cached_statistics")
def update_cached_statistics() -> dict:
    return asyncio.run(_update_cached_statistics_async())


async def _update_cached_statistics_async() -> dict:
    async with celery_db_session() as session:
        repository = AnalyticsRepository(session)
        stats = await repository.get_dashboard_statistics()
        stats["cached_at"] = datetime.now(UTC).isoformat()

    async with celery_redis_client() as redis_client:
        await redis_client.setex(
            "dashboard_stats",
            300,
            json.dumps(stats, default=str),
        )

    return {"status": "updated"}
