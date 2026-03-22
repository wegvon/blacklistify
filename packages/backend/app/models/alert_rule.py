from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = {"schema": "blacklistify"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(30), nullable=False)  # blacklist_detected, blacklist_rate_above, scan_failed
    threshold: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    subnet_filter: Mapped[str | None] = mapped_column(String(43), nullable=True)  # NULL = all subnets
    webhook_id: Mapped[int | None] = mapped_column(
        ForeignKey("blacklistify.webhooks.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    webhook = relationship("Webhook", back_populates="alert_rules")
