from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class SubnetStatus(Base):
    __tablename__ = "subnet_status"
    __table_args__ = {"schema": "blacklistify"}

    subnet_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Ripefy UUID
    subnet_cidr: Mapped[str] = mapped_column(String(43), nullable=False)
    total_ips: Mapped[int] = mapped_column(Integer, default=0)
    blacklisted_ips: Mapped[int] = mapped_column(Integer, default=0)
    clean_ips: Mapped[int] = mapped_column(Integer, default=0)
    blacklist_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0)
    worst_providers: Mapped[dict | None] = mapped_column(JSONB, default=list)
    last_scan_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
