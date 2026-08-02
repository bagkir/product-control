import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import check_db_connection, dispose_engine
from src.core.logging_config import setup_logging

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
