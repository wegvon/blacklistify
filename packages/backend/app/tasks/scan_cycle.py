"""Scan cycle orchestration — uses Supabase REST API for all DB ops."""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery
from app.core.config import settings
from app.db.client import db
from app.services.subnet_expander import cidr_to_ips, split_into_batches

logger = logging.getLogger(__name__)


def _fetch_blocks_with_prefix_info() -> list[dict]:
    blocks = db.get_all_blocks()
    prefixes = {p["id"]: p for p in db.get_all_prefixes()}

    enriched = []
    for block in blocks:
        prefix = prefixes.get(block.get("prefix_id", ""), {})
        enriched.append({
            "block_id": block["id"],
            "block_cidr": block["cidr"],
            "prefix_id": block.get("prefix_id", ""),
            "prefix_cidr": prefix.get("cidr", ""),
        })
    return enriched


@celery.task(bind=True, name="app.tasks.scan_cycle.run_sampling_scan")
def run_sampling_scan(self):
    """Sampling: 1 IP per /24 block (.1 address)."""
    try:
        job = db.create_scan_job({
            "job_type": "sampling",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Starting sampling scan job #%d", job["id"])

        blocks = _fetch_blocks_with_prefix_info()
        if not blocks:
            db.update_scan_job(job["id"], {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
            return

        db.update_scan_job(job["id"], {"total_subnets": len(blocks)})

        all_tasks = []
        batch_ips, batch_meta = [], []

        for block in blocks:
            network_part = block["block_cidr"].split("/")[0]
            parts = network_part.split(".")
            sample_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.1"

            batch_ips.append(sample_ip)
            batch_meta.append(block)

            if len(batch_ips) >= settings.scan_batch_size:
                all_tasks.append({"job_id": job["id"], "ips": batch_ips[:], "blocks": batch_meta[:]})
                batch_ips.clear()
                batch_meta.clear()

        if batch_ips:
            all_tasks.append({"job_id": job["id"], "ips": batch_ips[:], "blocks": batch_meta[:]})

        db.update_scan_job(job["id"], {"total_ips": len(blocks)})

        from app.tasks.scan_subnet import scan_block_batch
        for t in all_tasks:
            scan_block_batch.delay(job_id=t["job_id"], ips=t["ips"], blocks=t["blocks"])

        logger.info("Sampling scan #%d: %d batches, %d blocks", job["id"], len(all_tasks), len(blocks))

    except Exception as e:
        logger.exception("Sampling scan failed: %s", e)


@celery.task(bind=True, name="app.tasks.scan_cycle.run_full_scan")
def run_full_scan(self):
    """Full scan: all IPs in all /24 blocks."""
    try:
        job = db.create_scan_job({
            "job_type": "full",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Starting full scan job #%d", job["id"])

        blocks = _fetch_blocks_with_prefix_info()
        if not blocks:
            db.update_scan_job(job["id"], {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
            return

        db.update_scan_job(job["id"], {"total_subnets": len(blocks)})

        total_ips = 0
        all_tasks = []
        for block in blocks:
            ips = cidr_to_ips(block["block_cidr"])
            total_ips += len(ips)
            batches = split_into_batches(ips, settings.scan_batch_size)
            for batch in batches:
                all_tasks.append({"job_id": job["id"], "ips": batch, "blocks": [block] * len(batch)})

        db.update_scan_job(job["id"], {"total_ips": total_ips})

        from app.tasks.scan_subnet import scan_block_batch
        for t in all_tasks:
            scan_block_batch.delay(job_id=t["job_id"], ips=t["ips"], blocks=t["blocks"], bypass_cache=True)

        logger.info("Full scan #%d: %d batches, %d IPs, %d blocks", job["id"], len(all_tasks), total_ips, len(blocks))

    except Exception as e:
        logger.exception("Full scan failed: %s", e)


@celery.task(name="app.tasks.scan_cycle.refresh_subnet_status")
def refresh_subnet_status():
    """Refresh block_status from scan_results — uses Supabase REST API."""
    try:
        # Get all blocks with latest scan results grouped
        all_results = db.client.table("blf_scan_results").select(
            "block_id, block_cidr, prefix_id, prefix_cidr, ip_address, is_blacklisted, scan_job_id, checked_at"
        ).order("checked_at", desc=True).limit(50000).execute().data or []

        # Group by block
        from collections import defaultdict
        block_data = defaultdict(lambda: {"ips": set(), "blacklisted": 0, "last_job": 0, "last_checked": ""})

        for r in all_results:
            bid = r.get("block_id")
            if not bid:
                continue
            ip = r.get("ip_address", "")
            d = block_data[bid]
            if ip not in d["ips"]:  # Only count latest per IP
                d["ips"].add(ip)
                if r.get("is_blacklisted"):
                    d["blacklisted"] += 1
                d["block_cidr"] = r.get("block_cidr", "")
                d["prefix_id"] = r.get("prefix_id")
                d["prefix_cidr"] = r.get("prefix_cidr")
                job_id = r.get("scan_job_id", 0) or 0
                if job_id > d["last_job"]:
                    d["last_job"] = job_id
                checked = r.get("checked_at", "")
                if checked > d["last_checked"]:
                    d["last_checked"] = checked

        for block_id, d in block_data.items():
            total = len(d["ips"])
            bl = d["blacklisted"]
            rate = round(bl / total, 4) if total > 0 else 0

            db.upsert_block_status({
                "block_id": block_id,
                "block_cidr": d["block_cidr"],
                "prefix_id": d["prefix_id"],
                "prefix_cidr": d["prefix_cidr"],
                "total_ips": total,
                "blacklisted_ips": bl,
                "clean_ips": total - bl,
                "blacklist_rate": rate,
                "last_scan_job_id": d["last_job"] or None,
                "last_scanned_at": d["last_checked"] or None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        logger.info("Refreshed block status for %d blocks", len(block_data))

    except Exception as e:
        logger.exception("Failed to refresh block status: %s", e)
