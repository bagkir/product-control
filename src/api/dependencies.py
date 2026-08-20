from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import AppException
from src.data.repositories import (
    AnalyticsRepository,
    BatchRepository,
    ProductRepository,
    WorkCenterRepository,
)
from src.data.repositories.webhook_deliveries_repository import (
    WebhookDeliveryRepository,
)
from src.data.repositories.webhook_subscription_repository import (
    WebhookSubscriptionRepository,
)
from src.domain.services.analytics_service import AnalyticsService
from src.domain.services.batch_service import BatchService
from src.domain.services.product_service import ProductService
from src.domain.services.webhook_service import WebhookService

# ========== AUTH (п.5 code_review: базовая аутентификация через API-key) ==========

_api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Security(_api_key_header)] = None,
) -> None:
    """
    Проверить API-key из заголовка запроса.

    До этой правки любой, кто знает URL сервиса, мог создавать/удалять записи
    в каталоге без какой-либо аутентификации. Это простейший вариант защиты
    (единый ключ на всё API) — для реального продакшена стоит заменить на
    OAuth2/JWT с ключами per-client, но для MVP закрывает самую очевидную дыру.
    """
    if api_key is None or api_key != settings.API_KEY:
        raise AppException(message="Invalid or missing API key", status_code=401)


ApiKeyDep = Depends(verify_api_key)


# ========== REPOSITORIES ==========


async def get_product_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductRepository:
    """
    Создать ProductRepository для текущей сессии БД.

    Создается новый экземпляр для каждого запроса.
    """
    return ProductRepository(db)


async def get_batch_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchRepository:
    """
    Создать BatchRepository для текущей сессии БД.

    Создается новый экземпляр для каждого запроса.
    """
    return BatchRepository(db)


async def get_work_center_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkCenterRepository:
    """
    Создать WorkCenterRepository для текущей сессии БД.

    Создается новый экземпляр для каждого запроса.
    """
    return WorkCenterRepository(db)


async def get_webhook_subscription_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookSubscriptionRepository:
    return WebhookSubscriptionRepository(db)


async def get_analytic_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyticsRepository:
    return AnalyticsRepository(db)


async def get_webhook_delivery_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookDeliveryRepository:
    return WebhookDeliveryRepository(db)


# ========== SERVICES ==========


async def get_analytic_service(
    analytics_repository: Annotated[
        AnalyticsRepository,
        Depends(get_analytic_repository),
    ],
) -> AnalyticsService:
    return AnalyticsService(
        analytics_repository=analytics_repository,
    )


async def get_webhook_service(
    subscription_repository: Annotated[
        WebhookSubscriptionRepository, Depends(get_webhook_subscription_repository)
    ],
    delivery_repository: Annotated[
        WebhookDeliveryRepository, Depends(get_webhook_delivery_repository)
    ],
) -> WebhookService:
    return WebhookService(
        subscription_repository=subscription_repository,
        delivery_repository=delivery_repository,
    )


async def get_batch_service(
    batch_repository: Annotated[
        BatchRepository,
        Depends(get_batch_repository),
    ],
    work_center_repository: Annotated[
        WorkCenterRepository,
        Depends(get_work_center_repository),
    ],
    webhook_service: Annotated[
        WebhookService,
        Depends(get_webhook_service),
    ],
) -> BatchService:
    return BatchService(
        batch_repository=batch_repository,
        work_center_repository=work_center_repository,
        webhook_service=webhook_service,
    )


async def get_product_service(
    product_repository: Annotated[
        ProductRepository,
        Depends(get_product_repository),
    ],
    batch_repository: Annotated[
        BatchRepository,
        Depends(get_batch_repository),
    ],
    webhook_service: Annotated[
        WebhookService,
        Depends(get_webhook_service),
    ],
) -> ProductService:
    return ProductService(
        product_repository=product_repository,
        batch_repository=batch_repository,
        webhook_service=webhook_service,
    )


# ========== TYPE ALIASES ДЛЯ УДОБСТВА ==========

# Можно использовать в роутерах так:
# async def my_route(service: BookServiceDep):
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytic_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
BatchServiceDep = Annotated[BatchService, Depends(get_batch_service)]
BatchRepoDep = Annotated[BatchRepository, Depends(get_batch_repository)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
