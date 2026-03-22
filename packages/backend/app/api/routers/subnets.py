"""Subnet/block listing and status endpoints — all via Supabase REST API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.security import get_auth_context, require_scope, AuthContext
from app.db.client import db
from app.schemas.subnet import BlockResponse, BlockStatusResponse, PrefixResponse, SummaryResponse

router = APIRouter(prefix="/api/v1/subnets", tags=["subnets"])


@router.get("/prefixes", response_model=list[PrefixResponse])
def list_prefixes(auth: AuthContext = Depends(require_scope("read"))):
    prefixes = db.get_all_prefixes()
    return [PrefixResponse(id=p["id"], ripe_account_id=p.get("ripe_account_id"), cidr=p["cidr"], is_test=p.get("is_test", False), description=p.get("description")) for p in prefixes]


@router.get("/blocks", response_model=list[BlockResponse])
def list_blocks(status_filter: str | None = Query(None, alias="status"), auth: AuthContext = Depends(require_scope("read"))):
    blocks = db.get_all_blocks(status=status_filter)
    return [BlockResponse(id=b["id"], prefix_id=b.get("prefix_id", ""), cidr=b["cidr"], status=b.get("status", ""), current_lease_id=b.get("current_lease_id"), notes=b.get("notes")) for b in blocks]


@router.get("/summary", response_model=SummaryResponse)
def get_summary(auth: AuthContext = Depends(require_scope("read"))):
    statuses = db.get_all_block_statuses()
    total_blocks = len(statuses)
    total_ips = sum(s.get("total_ips", 0) for s in statuses)
    blacklisted = sum(s.get("blacklisted_ips", 0) for s in statuses)
    clean = sum(s.get("clean_ips", 0) for s in statuses)
    prefix_ids = set(s.get("prefix_id") for s in statuses if s.get("prefix_id"))

    return SummaryResponse(
        total_prefixes=len(prefix_ids), total_blocks=total_blocks,
        total_ips=total_ips, blacklisted_ips=blacklisted, clean_ips=clean,
        blacklist_rate=round(blacklisted / total_ips, 4) if total_ips > 0 else 0,
    )


@router.get("/blocks/{block_id}/status", response_model=BlockStatusResponse)
def get_block_status(block_id: str, auth: AuthContext = Depends(require_scope("read"))):
    s = db.get_block_status(block_id)
    if not s:
        raise HTTPException(404, "No scan data for this block yet")
    return BlockStatusResponse(
        block_id=s["block_id"], block_cidr=s["block_cidr"],
        prefix_id=s.get("prefix_id"), prefix_cidr=s.get("prefix_cidr"),
        customer_name=s.get("customer_name"), total_ips=s.get("total_ips", 0),
        blacklisted_ips=s.get("blacklisted_ips", 0), clean_ips=s.get("clean_ips", 0),
        blacklist_rate=float(s.get("blacklist_rate", 0)),
        worst_providers=s.get("worst_providers", []),
        last_scanned_at=s.get("last_scanned_at"),
    )


@router.get("/blocks/{block_id}/results")
def get_block_results(block_id: str, blacklisted_only: bool = Query(False), limit: int = Query(100, le=500), auth: AuthContext = Depends(require_scope("read"))):
    results = db.get_results_by_block(block_id, blacklisted_only=blacklisted_only, limit=limit)
    return [
        {"id": r["id"], "ip_address": str(r.get("ip_address", "")), "is_blacklisted": r.get("is_blacklisted", False), "providers_detected": r.get("providers_detected", []), "providers_total": r.get("providers_total", 0), "checked_at": r.get("checked_at")}
        for r in results
    ]


@router.post("/blocks/{block_id}/scan")
def trigger_block_scan(block_id: str, auth: AuthContext = Depends(require_scope("scan"))):
    block = db.get_block_by_id(block_id)
    if not block:
        raise HTTPException(404, "Block not found in Ripefy")

    prefix = db.get_prefix_by_id(block.get("prefix_id", ""))
    cidr = block.get("cidr", "")

    from app.services.subnet_expander import cidr_to_ips, split_into_batches

    ips = cidr_to_ips(cidr)
    job = db.create_scan_job({
        "job_type": "manual",
        "status": "running",
        "total_subnets": 1,
        "total_ips": len(ips),
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    block_meta = {
        "block_id": block["id"], "block_cidr": cidr,
        "prefix_id": block.get("prefix_id", ""),
        "prefix_cidr": prefix.get("cidr", "") if prefix else "",
    }

    from app.tasks.scan_subnet import scan_block_batch
    batches = split_into_batches(ips, settings.scan_batch_size)
    for batch in batches:
        scan_block_batch.delay(job_id=job["id"], ips=batch, blocks=[block_meta] * len(batch))

    return {"job_id": job["id"], "status": "running", "block_cidr": cidr, "total_ips": len(ips), "batches": len(batches)}
