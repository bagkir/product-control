import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import settings
from src.core.database import Base, get_db
from src.data.models import (
    Batch,
    Product,
    WebhookDelivery,
    WebhookSubscription,
    WorkCenter,
)
from src.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/product_control_test",
)


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    try:
        yield test_engine
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_database(
    engine: AsyncEngine,
) -> AsyncGenerator[None, None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def clean_db(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    for model in (
        WebhookDelivery,
        WebhookSubscription,
        Product,
        Batch,
        WorkCenter,
    ):
        await db_session.execute(model.__table__.delete())

    await db_session.commit()

    yield db_session


@pytest_asyncio.fixture
async def client(
    clean_db: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield clean_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        ac.headers["X-API-Key"] = settings.API_KEY
        yield ac

    app.dependency_overrides.clear()
