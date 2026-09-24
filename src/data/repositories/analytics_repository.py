from datetime import datetime, timezone, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Batch, Product, WorkCenter


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_statistics(self) -> dict:
        summary_query = (
            select(
                func.count(Batch.id).label("total_batches"),
                func.sum(case((Batch.is_closed.is_(False), 1), else_=0)).label(
                    "active_batches"
                ),
                func.count(Product.id).label("total_products"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                    "aggregated_products"
                ),
            )
            .select_from(Batch)
            .outerjoin(Product, Product.batch_id == Batch.id)
        )

        result = await self.session.execute(summary_query)
        row = result.first()
        total_batches = row.total_batches or 0
        active_batches = row.active_batches or 0
        closed_batches = total_batches - active_batches
        total_products = row.total_products or 0
        aggregated_products = row.aggregated_products or 0
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
        tomorrow = today + timedelta(days=1)

        # Используем диапазон вместо func.date()
        batches_created = await self._scalar(
            select(func.count(Batch.id)).where(
                Batch.batch_date >= today, Batch.batch_date < tomorrow
            )
        )
        batches_closed = await self._scalar(
            select(func.count(Batch.id)).where(
                Batch.batch_date >= today,
                Batch.batch_date < tomorrow,
                Batch.is_closed.is_(True),
            )
        )
        products_added = await self._scalar(
            select(func.count(Product.id)).where(
                Product.created_at >= today, Product.created_at < tomorrow
            )
        )
        products_aggregated = await self._scalar(
            select(func.count(Product.id)).where(
                Product.aggregated_at >= today,
                Product.aggregated_at < tomorrow,
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
