"""Dashboard aggregate statistics — all via Supabase REST API."""

from fastapi import APIRouter, Depends, Query

from app.core.security import get_auth_context, require_scope, AuthContext
from app.db.client import db

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/")
def get_dashboard_stats(auth: AuthContext = Depends(require_scope("read"))):
    statuses = db.get_all_block_statuses()
    total_blocks = len(statuses)
    prefix_ids = set(s.get("prefix_id") for s in statuses if s.get("prefix_id"))
    total_ips = sum(s.get("total_ips", 0) for s in statuses)
    blacklisted = sum(s.get("blacklisted_ips", 0) for s in statuses)

    # Last completed scan
    jobs = db.list_scan_jobs(limit=1, status="completed")
    last_job = jobs[0] if jobs else None

    # Running scans
    running_jobs = db.list_scan_jobs(limit=10, status="running")

    return {
        "total_prefixes": len(prefix_ids),
        "total_blocks": total_blocks,
        "total_ips": total_ips,
        "blacklisted_ips": blacklisted,
        "clean_ips": total_ips - blacklisted,
        "blacklist_rate": round(blacklisted / total_ips, 4) if total_ips > 0 else 0,
        "running_scans": len(running_jobs),
        "last_scan": {
            "job_id": last_job["id"],
            "type": last_job["job_type"],
            "completed_at": last_job.get("completed_at"),
            "scanned_ips": last_job.get("scanned_ips", 0),
            "blacklisted_ips": last_job.get("blacklisted_ips", 0),
        } if last_job else None,
    }


@router.get("/worst-blocks")
def get_worst_blocks(limit: int = Query(10, le=50), auth: AuthContext = Depends(require_scope("read"))):
    blocks = db.get_worst_blocks(limit=limit)
    return [
        {
            "block_id": b.get("block_id"),
            "block_cidr": b.get("block_cidr"),
            "prefix_cidr": b.get("prefix_cidr"),
            "customer_name": b.get("customer_name"),
            "total_ips": b.get("total_ips", 0),
            "blacklisted_ips": b.get("blacklisted_ips", 0),
            "blacklist_rate": float(b.get("blacklist_rate", 0)),
            "worst_providers": b.get("worst_providers", []),
            "last_scanned_at": b.get("last_scanned_at"),
        }
        for b in blocks
    ]
