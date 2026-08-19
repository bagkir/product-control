from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models import Batch, Product
from src.data.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[Batch]):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=Batch)

    async def get_by_id_with_products(self, batch_id: int) -> Batch | None:
        """Партия вместе с продукцией (для GET /batches/{id})."""
        stmt = (
            select(Batch)
            .options(selectinload(Batch.products))
            .where(Batch.id == batch_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_number_and_date(
        self, batch_number: int, batch_date: date
    ) -> bool:
        """Проверка уникального составного ключа перед созданием."""
        stmt = select(Batch.id).where(
            Batch.batch_number == batch_number,
            Batch.batch_date == batch_date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _build_filtered_stmt(
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
    ):
        stmt = select(Batch)

        if is_closed is not None:
            stmt = stmt.where(Batch.is_closed == is_closed)

        if batch_number is not None:
            stmt = stmt.where(Batch.batch_number == batch_number)

        if batch_date is not None:
            stmt = stmt.where(Batch.batch_date == batch_date)

        if date_from is not None:
            stmt = stmt.where(Batch.batch_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Batch.batch_date <= date_to)

        if work_center_id is not None:
            stmt = stmt.where(Batch.work_center_id == work_center_id)

        if shift is not None:
            stmt = stmt.where(Batch.shift == shift)

        return stmt

    async def list_filtered(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Batch], int]:
        """Список партий с фильтрами + общее количество для пагинации."""
        base_stmt = self._build_filtered_stmt(
            is_closed=is_closed,
            batch_number=batch_number,
            batch_date=batch_date,
            work_center_id=work_center_id,
            shift=shift,
        )

        total = await self.count(base_stmt)

        stmt = (
            base_stmt.options(selectinload(Batch.products))
            .order_by(Batch.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def list_for_export(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
    ) -> list[Batch]:
        stmt = (
            self._build_filtered_stmt(
                is_closed=is_closed,
                batch_number=batch_number,
                date_from=date_from,
                date_to=date_to,
                work_center_id=work_center_id,
                shift=shift,
            )
            .options(selectinload(Batch.work_center))
            .order_by(Batch.created_at.desc())
        )

        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def aggregate_batch(self, batch_id: int) -> int:
        """Агрегировать все неагрегированные продукты партии."""
        stmt = (
            update(Product)
            .where(Product.batch_id == batch_id, Product.is_aggregated == False)  # noqa
            .values(
                is_aggregated=True,
                aggregated_at=func.now(),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_full_for_report(self, batch_id: int) -> Batch | None:
        """
        Партия вместе с products И work_center — нужно для отчёта, где
        используются оба (в отличие от get_by_id_with_products, который
        грузит только products для BatchResponse).
        """
        stmt = (
            select(Batch)
            .options(
                selectinload(Batch.products),
                selectinload(Batch.work_center),
            )
            .where(Batch.id == batch_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def close_expired(self, now: datetime) -> list[Batch]:
        """
        Находит партии для автозакрытия (is_closed=False AND shift_end < now),
        закрывает их и возвращает список закрытых партий — с products
        (eager-loaded), чтобы вызывающий код мог опубликовать batch_closed
        со статистикой агрегации, не делая для этого отдельный запрос.
        """
        select_stmt = (
            select(Batch)
            .options(selectinload(Batch.products))
            .where(
                Batch.is_closed.is_(False),
                Batch.shift_end < now,
            )
        )
        result = await self.session.execute(select_stmt)
        expired_batches = list(result.scalars().all())

        if not expired_batches:
            return []

        ids = [b.id for b in expired_batches]
        await self.session.execute(
            update(Batch).where(Batch.id.in_(ids)).values(is_closed=True, closed_at=now)
        )

        for batch in expired_batches:
            batch.is_closed = True
            batch.closed_at = now

        return expired_batches
