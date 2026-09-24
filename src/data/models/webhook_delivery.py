from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("webhook_subscriptions.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    status: Mapped[str] = mapped_column(String(), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer(), default=0)
    response_status: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    response_body: Mapped[str | None] = mapped_column(String(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    subscription: Mapped["WebhookSubscription"] = relationship(  # noqa
        back_populates="deliveries"
    )
