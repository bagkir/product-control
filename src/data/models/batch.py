from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Статус
    is_closed: Mapped[bool] = mapped_column(Boolean(), default=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    # Описание задания
    task_description: Mapped[str] = mapped_column(Text(), nullable=False)
    work_center_id: Mapped[int] = mapped_column(
        ForeignKey("work_centers.id"), nullable=False
    )
    shift: Mapped[str] = mapped_column(String(), nullable=False)
    team: Mapped[str] = mapped_column(String(), nullable=False)

    # Идентификация партии
    batch_number: Mapped[int] = mapped_column(Integer(), nullable=False, index=True)
    batch_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)

    # Продукция
    nomenclature: Mapped[str] = mapped_column(String(100), nullable=False)
    ekn_code: Mapped[str] = mapped_column(String(), nullable=False)

    # Временные рамки
    shift_start: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    shift_end: Mapped[datetime] = mapped_column(DateTime(), nullable=False)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[list["Product"]] = relationship(back_populates="batch")  # noqa
    work_center: Mapped["WorkCenter"] = relationship(back_populates="batches")  # noqa

    __table_args__ = (
        UniqueConstraint("batch_number", "batch_date", name="uq_batch_number_date"),
        Index("idx_batch_closed", "is_closed"),
        Index("idx_batch_shift_times", "shift_start", "shift_end"),
    )
