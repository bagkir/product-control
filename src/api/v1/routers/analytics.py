from fastapi import APIRouter

from src.api.dependencies import AnalyticsServiceDep, ApiKeyDep
from src.api.v1.schemas.analytics import DashboardResponse

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[ApiKeyDep])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_stats(service: AnalyticsServiceDep):
    """
    Возвращает статистику дашборда из Redis-кэша.
    Кэш обновляется Celery Beat каждые 5 минут.
    """
    return await service.get_dashboard_statistics()
