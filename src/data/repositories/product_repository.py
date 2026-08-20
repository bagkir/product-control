from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Product
from src.data.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=Product)

    async def get_by_unique_code(self, unique_code: str) -> Product | None:
        stmt = select(Product).where(Product.unique_code == unique_code)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def aggregate_product(
        self,
        unique_code: str,
    ) -> Product | None:
        stmt = (
            update(Product)
            .where(
                Product.unique_code == unique_code,
                Product.is_aggregated.is_(False),
            )
            .values(
                is_aggregated=True,
                aggregated_at=func.now(),
            )
            .returning(Product)
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def aggregate_by_codes(self, batch_id: int, unique_codes: list[str]) -> dict:
        """
        Массовая агрегация по списку кодов внутри одной партии.

        Один SELECT, чтобы понять что есть/нет/уже агрегировано, и один
        bulk UPDATE на подходящие id — вместо N отдельных запросов на
        каждый код. Рассчитан на вызов чанками (см. aggregation_tasks.py),
        чтобы Celery-задача могла коммитить и репортить прогресс частями.
        """
        stmt = select(Product).where(
            Product.batch_id == batch_id,
            Product.unique_code.in_(unique_codes),
        )
        result = await self.session.execute(stmt)
        found: dict[str, Product] = {p.unique_code: p for p in result.scalars().all()}

        not_found = [c for c in unique_codes if c not in found]
        already_aggregated = [c for c, p in found.items() if p.is_aggregated]
        to_aggregate_ids = [p.id for p in found.values() if not p.is_aggregated]

        aggregated_count = 0
        if to_aggregate_ids:
            upd_stmt = (
                update(Product)
                .where(Product.id.in_(to_aggregate_ids))
                .values(is_aggregated=True, aggregated_at=func.now())
            )
            upd_result = await self.session.execute(upd_stmt)
            aggregated_count = upd_result.rowcount

        return {
            "aggregated": aggregated_count,
            "already_aggregated": already_aggregated,
            "not_found": not_found,
        }
