import json
from datetime import UTC, datetime

from src.core.redis_client import get_redis
from src.data.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    def __init__(self, analytics_repository: AnalyticsRepository):
        self.analytics_repository = analytics_repository

    async def get_dashboard_statistics(self) -> dict:
        redis = get_redis()

        cached_data = await redis.get("dashboard_stats")

        if cached_data is None:
            stats = await self.analytics_repository.get_dashboard_statistics()
            stats["cached_at"] = datetime.now(UTC).isoformat()

            await redis.setex(
                "dashboard_stats",
                300,
                json.dumps(stats, default=str),
            )

            return stats

        return json.loads(cached_data)
