from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ScanResult(Base):
    __tablename__ = "scan_results"
    __table_args__ = (
        {"schema": "blacklistify"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_job_id: Mapped[int] = mapped_column(
        ForeignKey("blacklistify.scan_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Ripefy references (soft FKs — no hard FK to public schema)
    block_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    block_cidr: Mapped[str] = mapped_column(String(43), nullable=False, index=True)  # e.g. "185.87.120.0/24"
    prefix_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    prefix_cidr: Mapped[str | None] = mapped_column(String(43), nullable=True)  # e.g. "185.87.120.0/22"

    ip_address: Mapped[str] = mapped_column(INET, nullable=False, index=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    providers_detected: Mapped[dict | None] = mapped_column(JSONB, default=list)
    providers_total: Mapped[int] = mapped_column(Integer, default=0)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan_job = relationship("ScanJob", back_populates="results")
