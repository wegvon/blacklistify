"""Dashboard aggregate statistics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import get_auth_context, require_scope, AuthContext
from app.db.session import get_db
from app.models.scan_job import ScanJob
from app.models.subnet_status import BlockStatus

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/")
def get_dashboard_stats(
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get overall dashboard statistics."""
    statuses = db.query(BlockStatus).all()

    total_blocks = len(statuses)
    prefix_ids = set(s.prefix_id for s in statuses if s.prefix_id)
    total_ips = sum(s.total_ips for s in statuses)
    blacklisted = sum(s.blacklisted_ips for s in statuses)
    clean = total_ips - blacklisted

    last_job = db.query(ScanJob).filter_by(status="completed").order_by(ScanJob.completed_at.desc()).first()
    running = db.query(ScanJob).filter_by(status="running").count()

    return {
        "total_prefixes": len(prefix_ids),
        "total_blocks": total_blocks,
        "total_ips": total_ips,
        "blacklisted_ips": blacklisted,
        "clean_ips": clean,
        "blacklist_rate": round(blacklisted / total_ips, 4) if total_ips > 0 else 0,
        "running_scans": running,
        "last_scan": {
            "job_id": last_job.id,
            "type": last_job.job_type,
            "completed_at": last_job.completed_at.isoformat() if last_job.completed_at else None,
            "scanned_ips": last_job.scanned_ips,
            "blacklisted_ips": last_job.blacklisted_ips,
        } if last_job else None,
    }


@router.get("/worst-blocks")
def get_worst_blocks(
    limit: int = Query(10, le=50),
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get /24 blocks with the highest blacklist rates."""
    blocks = (
        db.query(BlockStatus)
        .filter(BlockStatus.blacklisted_ips > 0)
        .order_by(BlockStatus.blacklist_rate.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "block_id": b.block_id,
            "block_cidr": b.block_cidr,
            "prefix_cidr": b.prefix_cidr,
            "customer_name": b.customer_name,
            "total_ips": b.total_ips,
            "blacklisted_ips": b.blacklisted_ips,
            "blacklist_rate": float(b.blacklist_rate),
            "worst_providers": b.worst_providers or [],
            "last_scanned_at": b.last_scanned_at.isoformat() if b.last_scanned_at else None,
        }
        for b in blocks
    ]


@router.get("/timeline")
def get_blacklist_timeline(
    days: int = Query(30, le=90),
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get blacklist trend over the last N days."""
    query = text("""
        SELECT
            DATE(checked_at) as scan_date,
            COUNT(*) as total_checked,
            COUNT(*) FILTER (WHERE is_blacklisted = TRUE) as blacklisted
        FROM blacklistify.scan_results
        WHERE checked_at >= NOW() - INTERVAL :days_interval
        GROUP BY DATE(checked_at)
        ORDER BY scan_date ASC
    """)

    results = db.execute(query, {"days_interval": f"{days} days"}).fetchall()

    return [
        {
            "date": str(row[0]),
            "total_checked": row[1],
            "blacklisted": row[2],
            "blacklist_rate": round(row[2] / row[1], 4) if row[1] > 0 else 0,
        }
        for row in results
    ]
