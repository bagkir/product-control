from contextlib import asynccontextmanager
from functools import lru_cache

import redis.asyncio as redis

from src.core.config import settings


@lru_cache
def get_redis() -> redis.Redis:
    """Возвращает асинхронный клиент Redis."""
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=10,
    )


async def close_redis() -> None:
    client = get_redis()
    await client.aclose()
    get_redis.cache_clear()


@asynccontextmanager
async def celery_redis_client():
    """
    Redis-клиент для использования ВНУТРИ Celery-задач.

    В отличие от get_redis() (module-level @lru_cache, общий на весь
    FastAPI-процесс), здесь клиент создаётся заново на каждый вызов и
    закрывается в конце. Причина та же, что для celery_db_session():
    каждый вызов Celery-задачи оборачивается в свой asyncio.run() (свой
    event loop), а закэшированный get_redis()-клиент привязывается к
    первому loop'у, в котором был использован, и падает с
    "Event loop is closed" на следующем вызове задачи.
    """
    client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.aclose()
