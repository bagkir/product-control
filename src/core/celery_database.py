from contextlib import asynccontextmanager

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings


@asynccontextmanager
async def celery_db_session():
    """
    Сессия БД для использования внутри Celery-задач.

    В отличие от src.core.database.AsyncSessionLocal (module-level, общий
    для всего FastAPI-процесса), здесь engine создаётся заново на каждый
    вызов и гарантированно закрывается через dispose() в конце. Это нужно,
    потому что каждый вызов Celery-задачи оборачивается в свой asyncio.run()
    (свой event loop), а pool общего engine привязывается к первому loop'у,
    в котором был использован, и падает с "attached to a different loop"
    на следующем вызове.
    """
    engine = create_async_engine(str(settings.DATABASE_URL), poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
