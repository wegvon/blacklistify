from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ScanJob(Base):
    __tablename__ = "scan_jobs"
    __table_args__ = {"schema": "blacklistify"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)  # sampling, full, single, manual
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    total_subnets: Mapped[int] = mapped_column(Integer, default=0)
    total_ips: Mapped[int] = mapped_column(Integer, default=0)
    scanned_ips: Mapped[int] = mapped_column(Integer, default=0)
    blacklisted_ips: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    results = relationship("ScanResult", back_populates="scan_job", cascade="all, delete-orphan")
