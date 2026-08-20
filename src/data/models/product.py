from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    unique_code: Mapped[str] = mapped_column(
        String(), unique=True, nullable=False, index=True
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id"), nullable=False, index=True
    )

    # Агрегация
    is_aggregated: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
    aggregated_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    batch: Mapped["Batch"] = relationship(back_populates="products")  # noqa

    __table_args__ = (
        Index("idx_product_batch_aggregated", "batch_id", "is_aggregated"),
    )
