"""Scan job management endpoints — all via Supabase REST API."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_auth_context, require_scope, AuthContext
from app.db.client import db
from app.schemas.scan import ScanJobResponse, ScanTriggerRequest

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


@router.post("/")
def trigger_scan(body: ScanTriggerRequest, auth: AuthContext = Depends(require_scope("scan"))):
    if body.job_type == "sampling":
        from app.tasks.scan_cycle import run_sampling_scan
        run_sampling_scan.delay()
        return {"message": "Sampling scan triggered", "job_type": "sampling"}
    elif body.job_type == "full":
        from app.tasks.scan_cycle import run_full_scan
        run_full_scan.delay()
        return {"message": "Full scan triggered", "job_type": "full"}
    else:
        raise HTTPException(400, "Invalid job_type. Use: sampling or full")


@router.get("/", response_model=list[ScanJobResponse])
def list_scan_jobs(status_filter: str | None = Query(None, alias="status"), limit: int = Query(20, le=100), auth: AuthContext = Depends(require_scope("read"))):
    jobs = db.list_scan_jobs(limit=limit, status=status_filter)
    return [
        ScanJobResponse(
            id=j["id"], job_type=j["job_type"], status=j["status"],
            total_subnets=j.get("total_subnets", 0), total_ips=j.get("total_ips", 0),
            scanned_ips=j.get("scanned_ips", 0), blacklisted_ips=j.get("blacklisted_ips", 0),
            started_at=j.get("started_at"), completed_at=j.get("completed_at"),
            error_message=j.get("error_message"), created_at=j["created_at"],
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=ScanJobResponse)
def get_scan_job(job_id: int, auth: AuthContext = Depends(require_scope("read"))):
    j = db.get_scan_job(job_id)
    if not j:
        raise HTTPException(404, "Scan job not found")
    return ScanJobResponse(
        id=j["id"], job_type=j["job_type"], status=j["status"],
        total_subnets=j.get("total_subnets", 0), total_ips=j.get("total_ips", 0),
        scanned_ips=j.get("scanned_ips", 0), blacklisted_ips=j.get("blacklisted_ips", 0),
        started_at=j.get("started_at"), completed_at=j.get("completed_at"),
        error_message=j.get("error_message"), created_at=j["created_at"],
    )


@router.get("/{job_id}/results")
def get_scan_job_results(job_id: int, blacklisted_only: bool = Query(False), limit: int = Query(100, le=500), auth: AuthContext = Depends(require_scope("read"))):
    j = db.get_scan_job(job_id)
    if not j:
        raise HTTPException(404, "Scan job not found")
    results = db.get_results_by_job(job_id, blacklisted_only=blacklisted_only, limit=limit)
    return {
        "job_id": job_id,
        "total": len(results),
        "results": [
            {"id": r["id"], "block_cidr": r.get("block_cidr", ""), "ip_address": str(r.get("ip_address", "")), "is_blacklisted": r.get("is_blacklisted", False), "providers_detected": r.get("providers_detected", []), "providers_total": r.get("providers_total", 0), "checked_at": r.get("checked_at")}
            for r in results
        ],
    }
