"""Scan job management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_auth_context, require_scope, AuthContext
from app.db.session import get_db
from app.models.scan_job import ScanJob
from app.models.scan_result import ScanResult
from app.schemas.scan import ScanJobResponse, ScanTriggerRequest

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


@router.post("/")
def trigger_scan(
    body: ScanTriggerRequest,
    auth: AuthContext = Depends(require_scope("scan")),
    db: Session = Depends(get_db),
):
    """Trigger a manual scan cycle."""
    if body.job_type == "sampling":
        from app.tasks.scan_cycle import run_sampling_scan
        run_sampling_scan.delay()
        return {"message": "Sampling scan triggered", "job_type": "sampling"}

    elif body.job_type == "full":
        from app.tasks.scan_cycle import run_full_scan
        run_full_scan.delay()
        return {"message": "Full scan triggered", "job_type": "full"}

    elif body.job_type == "single" and body.subnet_id:
        # Delegate to subnet-specific scan
        from app.api.routers.subnets import trigger_subnet_scan
        # This is handled by the subnets router
        return {"message": "Use /api/v1/subnets/{id}/scan for single subnet scans"}

    else:
        raise HTTPException(400, "Invalid job_type. Use: sampling, full, or single (with subnet_id)")


@router.get("/", response_model=list[ScanJobResponse])
def list_scan_jobs(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, le=100),
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """List scan jobs, newest first."""
    query = db.query(ScanJob)

    if status_filter:
        query = query.filter_by(status=status_filter)

    jobs = query.order_by(ScanJob.created_at.desc()).limit(limit).all()

    return [
        ScanJobResponse(
            id=j.id,
            job_type=j.job_type,
            status=j.status,
            total_subnets=j.total_subnets or 0,
            total_ips=j.total_ips or 0,
            scanned_ips=j.scanned_ips or 0,
            blacklisted_ips=j.blacklisted_ips or 0,
            started_at=j.started_at.isoformat() if j.started_at else None,
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
            error_message=j.error_message,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=ScanJobResponse)
def get_scan_job(
    job_id: int,
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get details of a specific scan job."""
    job = db.query(ScanJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Scan job not found")

    return ScanJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_subnets=job.total_subnets or 0,
        total_ips=job.total_ips or 0,
        scanned_ips=job.scanned_ips or 0,
        blacklisted_ips=job.blacklisted_ips or 0,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
    )


@router.get("/{job_id}/results")
def get_scan_job_results(
    job_id: int,
    blacklisted_only: bool = Query(False),
    limit: int = Query(100, le=500),
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get results for a specific scan job."""
    job = db.query(ScanJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Scan job not found")

    query = db.query(ScanResult).filter_by(scan_job_id=job_id)
    if blacklisted_only:
        query = query.filter_by(is_blacklisted=True)

    results = query.order_by(ScanResult.checked_at.desc()).limit(limit).all()

    return {
        "job_id": job_id,
        "total": len(results),
        "results": [
            {
                "id": r.id,
                "subnet_cidr": r.subnet_cidr,
                "ip_address": str(r.ip_address),
                "is_blacklisted": r.is_blacklisted,
                "providers_detected": r.providers_detected or [],
                "providers_total": r.providers_total,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
            }
            for r in results
        ],
    }
