from celery import Celery
from celery.schedules import crontab

from src.core.config import settings

celery_app = Celery(
    "product_control",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.tasks.aggregation",
        "src.tasks.reports",
        "src.tasks.imports",
        "src.tasks.exports",
        "src.tasks.webhooks",
        "src.tasks.scheduled",
    ],
)

celery_app.conf.beat_schedule = {
    "auto-close-expired-batches": {
        "task": "tasks.auto_close_expired_batches",
        "schedule": crontab(hour=1, minute=0),
    },
    "cleanup-old-files": {
        "task": "tasks.cleanup_old_files",
        "schedule": crontab(hour=2, minute=0),
    },
    "update-statistics": {
        "task": "tasks.update_cached_statistics",
        "schedule": crontab(minute="*/5"),
    },
    "retry-failed-webhooks": {
        "task": "tasks.retry_failed_webhooks",
        "schedule": crontab(minute="*/15"),
    },
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)
