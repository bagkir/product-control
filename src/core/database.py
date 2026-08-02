import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(  # движок
    settings.DATABASE_URL.__str__(),
    pool_size=settings.DATABASE_POOL_SIZE,
    echo=settings.DEBUG,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)
async_session_maker = async_sessionmaker(  # фабрика сессий
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class Base(DeclarativeBase):
    pass


def init_db():
    pass


async def check_db_connection() -> bool:
    """
    Проверка подключения к БД.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database connection check failed")
        return False


async def dispose_engine() -> None:
    """Закрыть все соединения с БД."""
    await engine.dispose()