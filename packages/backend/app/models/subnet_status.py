"""
Aggregate blacklist status per ip_block (/24).
Refreshed periodically by Celery task from scan_results.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class BlockStatus(Base):
    """Blacklist status cache per /24 block (maps to Ripefy ip_blocks)."""
    __tablename__ = "block_status"
    __table_args__ = {"schema": "blacklistify"}

    block_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Ripefy ip_blocks.id
    block_cidr: Mapped[str] = mapped_column(String(43), nullable=False)  # e.g. "185.87.120.0/24"
    prefix_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # Ripefy ip_prefixes.id
    prefix_cidr: Mapped[str | None] = mapped_column(String(43), nullable=True)  # e.g. "185.87.120.0/22"
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
