"""Subnet listing and status endpoints (reads from Ripefy Supabase + blacklistify schema)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_auth_context, require_scope, AuthContext
from app.db.session import get_db
from app.db.supabase_read import subnet_reader
from app.models.scan_result import ScanResult
from app.models.subnet_status import SubnetStatus
from app.schemas.subnet import SubnetResponse, SubnetStatusResponse, SubnetSummaryResponse

router = APIRouter(prefix="/api/v1/subnets", tags=["subnets"])


@router.get("/", response_model=list[SubnetResponse])
def list_subnets(
    auth: AuthContext = Depends(require_scope("read")),
):
    """List all active subnets from Ripefy."""
    try:
        subnets = subnet_reader.get_active_subnets()
    except Exception as e:
        raise HTTPException(503, f"Failed to read subnets: {e}")

    return [
        SubnetResponse(
            id=s.get("id", ""),
            cidr=s.get("cidr", ""),
            description=s.get("description"),
            status=s.get("status", ""),
            customer_id=s.get("customer_id"),
        )
        for s in subnets
    ]


@router.get("/summary", response_model=SubnetSummaryResponse)
def get_subnets_summary(
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Aggregate blacklist status across all subnets."""
    statuses = db.query(SubnetStatus).all()

    total_subnets = len(statuses)
    total_ips = sum(s.total_ips for s in statuses)
    blacklisted = sum(s.blacklisted_ips for s in statuses)
    clean = sum(s.clean_ips for s in statuses)
    rate = round(blacklisted / total_ips, 4) if total_ips > 0 else 0.0

    # Last scan info
    last_scan = None
    latest = max(statuses, key=lambda s: s.last_scanned_at or "", default=None)
    if latest and latest.last_scan_job_id:
        from app.models.scan_job import ScanJob
        job = db.query(ScanJob).filter_by(id=latest.last_scan_job_id).first()
        if job:
            duration = None
            if job.started_at and job.completed_at:
                duration = int((job.completed_at - job.started_at).total_seconds())
            last_scan = {
                "job_id": job.id,
                "type": job.job_type,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration_seconds": duration,
            }

    return SubnetSummaryResponse(
        total_subnets=total_subnets,
        total_ips=total_ips,
        blacklisted_ips=blacklisted,
        clean_ips=clean,
        blacklist_rate=rate,
        last_scan=last_scan,
    )


@router.get("/{subnet_id}", response_model=SubnetResponse)
def get_subnet(
    subnet_id: str,
    auth: AuthContext = Depends(require_scope("read")),
):
    """Get a single subnet by ID from Ripefy."""
    subnet = subnet_reader.get_subnet_by_id(subnet_id)
    if not subnet:
        raise HTTPException(404, "Subnet not found")

    return SubnetResponse(
        id=subnet.get("id", ""),
        cidr=subnet.get("cidr", ""),
        description=subnet.get("description"),
        status=subnet.get("status", ""),
        customer_id=subnet.get("customer_id"),
    )


@router.get("/{subnet_id}/status", response_model=SubnetStatusResponse)
def get_subnet_status(
    subnet_id: str,
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get blacklist status for a specific subnet."""
    status = db.query(SubnetStatus).filter_by(subnet_id=subnet_id).first()
    if not status:
        raise HTTPException(404, "No scan data for this subnet yet")

    return SubnetStatusResponse(
        subnet_id=status.subnet_id,
        subnet_cidr=status.subnet_cidr,
        total_ips=status.total_ips,
        blacklisted_ips=status.blacklisted_ips,
        clean_ips=status.clean_ips,
        blacklist_rate=float(status.blacklist_rate),
        worst_providers=status.worst_providers or [],
        last_scanned_at=status.last_scanned_at.isoformat() if status.last_scanned_at else None,
    )


@router.get("/{subnet_id}/results")
def get_subnet_results(
    subnet_id: str,
    blacklisted_only: bool = Query(False),
    limit: int = Query(100, le=500),
    auth: AuthContext = Depends(require_scope("read")),
    db: Session = Depends(get_db),
):
    """Get scan results for a specific subnet."""
    query = db.query(ScanResult).filter_by(subnet_id=subnet_id)

    if blacklisted_only:
        query = query.filter_by(is_blacklisted=True)

    results = query.order_by(ScanResult.checked_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "ip_address": str(r.ip_address),
            "is_blacklisted": r.is_blacklisted,
            "providers_detected": r.providers_detected or [],
            "providers_total": r.providers_total,
            "checked_at": r.checked_at.isoformat() if r.checked_at else None,
        }
        for r in results
    ]


@router.post("/{subnet_id}/scan")
def trigger_subnet_scan(
    subnet_id: str,
    auth: AuthContext = Depends(require_scope("scan")),
    db: Session = Depends(get_db),
):
    """Trigger a manual scan for a specific subnet."""
    subnet = subnet_reader.get_subnet_by_id(subnet_id)
    if not subnet:
        raise HTTPException(404, "Subnet not found")

    from app.models.scan_job import ScanJob
    from app.services.subnet_expander import cidr_to_ips, split_into_batches
    from app.core.config import settings
    from datetime import datetime, timezone

    cidr = subnet.get("cidr", "")
    ips = cidr_to_ips(cidr)

    job = ScanJob(
        job_type="manual",
        status="running",
        total_subnets=1,
        total_ips=len(ips),
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.tasks.scan_subnet import scan_ip_batch
    batches = split_into_batches(ips, settings.scan_batch_size)
    for batch in batches:
        scan_ip_batch.delay(
            job_id=job.id,
            subnet_id=subnet_id,
            subnet_cidr=cidr,
            ips=batch,
        )

    return {
        "job_id": job.id,
        "status": "running",
        "total_ips": len(ips),
        "batches": len(batches),
    }
