from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Batch, Product, WorkCenter


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_statistics(self) -> dict:
        total_batches = await self._scalar(select(func.count(Batch.id)))

        active_batches = await self._scalar(
            select(func.count(Batch.id)).where(Batch.is_closed.is_(False))
        )

        closed_batches = total_batches - active_batches

        total_products = await self._scalar(select(func.count(Product.id)))

        aggregated_products = await self._scalar(
            select(func.count(Product.id)).where(Product.is_aggregated.is_(True))
        )

        aggregation_rate = (
            round(aggregated_products / total_products * 100, 2)
            if total_products
            else 0.0
        )

        today_stats = await self._get_today_statistics()
        by_shift = await self._get_shift_statistics()
        top_work_centers = await self._get_top_work_centers()

        return {
            "summary": {
                "total_batches": total_batches,
                "active_batches": active_batches,
                "closed_batches": closed_batches,
                "total_products": total_products,
                "aggregated_products": aggregated_products,
                "aggregation_rate": aggregation_rate,
            },
            "today": today_stats,
            "by_shift": by_shift,
            "top_work_centers": top_work_centers,
        }

    async def _get_today_statistics(self) -> dict:
        today = datetime.now(timezone.utc).date()

        batches_created = await self._scalar(
            select(func.count(Batch.id)).where(Batch.batch_date == today)
        )

        batches_closed = await self._scalar(
            select(func.count(Batch.id)).where(
                Batch.batch_date == today,
                Batch.is_closed.is_(True),
            )
        )

        products_added = await self._scalar(
            select(func.count(Product.id)).where(func.date(Product.created_at) == today)
        )

        products_aggregated = await self._scalar(
            select(func.count(Product.id)).where(
                func.date(Product.aggregated_at) == today,
                Product.is_aggregated.is_(True),
            )
        )

        return {
            "batches_created": batches_created,
            "batches_closed": batches_closed,
            "products_added": products_added,
            "products_aggregated": products_aggregated,
        }

    async def _get_shift_statistics(self) -> dict:
        result = await self.session.execute(
            select(
                Batch.shift,
                func.count(func.distinct(Batch.id)).label("batches"),
                func.count(Product.id).label("products"),
                func.count(case((Product.is_aggregated.is_(True), 1))).label(
                    "aggregated"
                ),
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(Batch.shift)
        )

        return {
            shift: {
                "batches": batches,
                "products": products,
                "aggregated": aggregated,
            }
            for shift, batches, products, aggregated in result.all()
        }

    async def _get_top_work_centers(self, limit: int = 10) -> list[dict]:
        result = await self.session.execute(
            select(
                WorkCenter.id,
                WorkCenter.identifier,
                WorkCenter.name,
                func.count(func.distinct(Batch.id)).label("batches_count"),
                func.count(Product.id).label("products_count"),
                func.count(case((Product.is_aggregated.is_(True), 1))).label(
                    "aggregated_count"
                ),
            )
            .join(Batch, Batch.work_center_id == WorkCenter.id)
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(
                WorkCenter.id,
                WorkCenter.identifier,
                WorkCenter.name,
            )
            .order_by(func.count(func.distinct(Batch.id)).desc())
            .limit(limit)
        )

        return [
            {
                "id": identifier,
                "name": name,
                "batches_count": batches_count,
                "products_count": products_count,
                "aggregation_rate": (
                    round(aggregated_count / products_count * 100, 2)
                    if products_count
                    else 0.0
                ),
            }
            for (
                _id,
                identifier,
                name,
                batches_count,
                products_count,
                aggregated_count,
            ) in result.all()
        ]

    async def _scalar(self, query) -> int:
        result = await self.session.execute(query)
        return result.scalar_one() or 0
