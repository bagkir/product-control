import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.routers import (
    batches_router,
    products_router,
    tasks_router,
    webhooks_router,
)
from src.api.v1.routers.analytics import router as analytics_router
from src.core.config import settings
from src.core.database import check_db_connection, dispose_engine
from src.core.exceptions import (
    register_exception_handlers,
    register_unhandled_exception_handler,
)
from src.core.logging_config import setup_logging
from src.core.redis_client import close_redis

logger = logging.getLogger(__name__)


# ========== LIFECYCLE EVENTS ==========


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager для FastAPI.

    Выполняется при:
    - startup: настройка логирования
    - shutdown: закрытие подключений к БД
    """
    # Startup
    setup_logging()
    if not await check_db_connection():
        logger.critical("Database is unreachable — aborting startup")
        raise RuntimeError("Database connection check failed on startup")
    logger.info("Application started")

    yield
    await close_redis()
    await dispose_engine()

    logger.info("Application stopped")


# ========== CREATE APP ==========

app = FastAPI(
    title=settings.APP_NAME,
    description="REST API для управления библиотечным каталогом",
    version="1.0.0",
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    lifespan=lifespan,
)

# ========== MIDDLEWARE ==========

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== EXCEPTION HANDLERS ==========

register_exception_handlers(app)
register_unhandled_exception_handler(app)

# ========== ROUTERS ==========

# Версия 1 API
app.include_router(router=batches_router, prefix=settings.API_V1_PREFIX)

app.include_router(router=products_router, prefix=settings.API_V1_PREFIX)

app.include_router(router=tasks_router, prefix=settings.API_V1_PREFIX)

app.include_router(router=webhooks_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {"message": "Welcome to Product Control API"}


@app.get("/health")
async def health_check():
    """Health check эндпоинт."""
    return {"status": "healthy"}


# Для запуска через python -m
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
