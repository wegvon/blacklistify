"""
Scan cycle orchestration tasks.
Reads ip_blocks (/24) from Ripefy Supabase, dispatches DNSBL checks.

Real Ripefy structure:
  ip_prefixes (/22, 77 rows) -> ip_blocks (/24, 308 rows, ~78K IPs)
  Scan unit = ip_block (/24 = 254 usable IPs)
"""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.supabase_read import subnet_reader
from app.models.scan_job import ScanJob
from app.models.subnet_status import BlockStatus
from app.services.subnet_expander import cidr_to_ips, split_into_batches

logger = logging.getLogger(__name__)


def _fetch_blocks_with_prefix_info() -> list[dict]:
    """
    Fetch all ip_blocks from Ripefy and enrich with prefix info.
    Returns list of dicts with block_id, block_cidr, prefix_id, prefix_cidr.
    """
    blocks = subnet_reader.get_all_blocks()
    prefixes = {p["id"]: p for p in subnet_reader.get_all_prefixes()}

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
    """
    Sampling scan: pick 1 representative IP per /24 block.
    Since all blocks are /24, we just check .1 of each block.
    Runs every N hours (configured via SCAN_INTERVAL_HOURS).
    """
    db = SessionLocal()
    try:
        job = ScanJob(
            job_type="sampling",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info("Starting sampling scan job #%d", job.id)

        try:
            blocks = _fetch_blocks_with_prefix_info()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed to read blocks from Ripefy: {e}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error("Sampling scan failed: %s", e)
            return

        if not blocks:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("No blocks found, scan completed")
            return

        job.total_subnets = len(blocks)

        # For sampling: 1 IP per /24 block (the .1 address)
        all_tasks = []
        total_ips = 0
        batch_ips = []
        batch_meta = []

        for block in blocks:
            cidr = block["block_cidr"]
            # Get .1 address as representative sample
            network_part = cidr.split("/")[0]
            parts = network_part.split(".")
            sample_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.1"

            batch_ips.append(sample_ip)
            batch_meta.append(block)
            total_ips += 1

            if len(batch_ips) >= settings.scan_batch_size:
                all_tasks.append({
                    "job_id": job.id,
                    "ips": batch_ips[:],
                    "blocks": batch_meta[:],
                })
                batch_ips.clear()
                batch_meta.clear()

        # Remaining batch
        if batch_ips:
            all_tasks.append({
                "job_id": job.id,
                "ips": batch_ips[:],
                "blocks": batch_meta[:],
            })

        job.total_ips = total_ips
        db.commit()

        from app.tasks.scan_subnet import scan_block_batch
        for task_data in all_tasks:
            scan_block_batch.delay(
                job_id=task_data["job_id"],
                ips=task_data["ips"],
                blocks=task_data["blocks"],
            )

        logger.info(
            "Sampling scan job #%d: dispatched %d batches for %d blocks",
            job.id, len(all_tasks), len(blocks),
        )

    except Exception as e:
        logger.exception("Sampling scan failed: %s", e)
    finally:
        db.close()


@celery.task(bind=True, name="app.tasks.scan_cycle.run_full_scan")
def run_full_scan(self):
    """
    Full scan: scan ALL IPs in ALL /24 blocks (254 IPs each).
    308 blocks x 254 IPs = ~78K IPs.
    Runs weekly, bypasses cache.
    """
    db = SessionLocal()
    try:
        job = ScanJob(
            job_type="full",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info("Starting full scan job #%d", job.id)

        try:
            blocks = _fetch_blocks_with_prefix_info()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed to read blocks from Ripefy: {e}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        if not blocks:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        job.total_subnets = len(blocks)
        total_ips = 0
        all_tasks = []

        for block in blocks:
            cidr = block["block_cidr"]
            ips = cidr_to_ips(cidr)
            total_ips += len(ips)

            batches = split_into_batches(ips, settings.scan_batch_size)
            for batch in batches:
                all_tasks.append({
                    "job_id": job.id,
                    "ips": batch,
                    "blocks": [block] * len(batch),  # Each IP maps to same block
                })

        job.total_ips = total_ips
        db.commit()

        from app.tasks.scan_subnet import scan_block_batch
        for task_data in all_tasks:
            scan_block_batch.delay(
                job_id=task_data["job_id"],
                ips=task_data["ips"],
                blocks=task_data["blocks"],
                bypass_cache=True,
            )

        logger.info(
            "Full scan job #%d: dispatched %d batches for %d IPs across %d blocks",
            job.id, len(all_tasks), total_ips, len(blocks),
        )

    except Exception as e:
        logger.exception("Full scan failed: %s", e)
    finally:
        db.close()


@celery.task(name="app.tasks.scan_cycle.refresh_subnet_status")
def refresh_subnet_status():
    """
    Recalculate block_status from latest scan_results.
    Runs every 30 minutes.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import text

        query = text("""
            WITH latest_results AS (
                SELECT DISTINCT ON (ip_address, block_cidr)
                    block_id,
                    block_cidr,
                    prefix_id,
                    prefix_cidr,
                    ip_address,
                    is_blacklisted,
                    providers_detected,
                    scan_job_id,
                    checked_at
                FROM blacklistify.scan_results
                ORDER BY ip_address, block_cidr, checked_at DESC
            )
            SELECT
                block_id,
                block_cidr,
                prefix_id,
                prefix_cidr,
                COUNT(*) as total_ips,
                COUNT(*) FILTER (WHERE is_blacklisted = TRUE) as blacklisted_ips,
                COUNT(*) FILTER (WHERE is_blacklisted = FALSE) as clean_ips,
                MAX(scan_job_id) as last_scan_job_id,
                MAX(checked_at) as last_scanned_at
            FROM latest_results
            WHERE block_id IS NOT NULL
            GROUP BY block_id, block_cidr, prefix_id, prefix_cidr
        """)

        results = db.execute(query).fetchall()

        for row in results:
            block_id = row[0]
            total = row[4]
            blacklisted = row[5]
            rate = round(blacklisted / total, 4) if total > 0 else 0

            existing = db.query(BlockStatus).filter_by(block_id=block_id).first()
            if existing:
                old_blacklisted = existing.blacklisted_ips
                existing.block_cidr = row[1]
                existing.prefix_id = row[2]
                existing.prefix_cidr = row[3]
                existing.total_ips = total
                existing.blacklisted_ips = blacklisted
                existing.clean_ips = row[6]
                existing.blacklist_rate = rate
                existing.last_scan_job_id = row[7]
                existing.last_scanned_at = row[8]
                if old_blacklisted != blacklisted:
                    existing.status_changed_at = datetime.now(timezone.utc)
            else:
                new_status = BlockStatus(
                    block_id=block_id,
                    block_cidr=row[1],
                    prefix_id=row[2],
                    prefix_cidr=row[3],
                    total_ips=total,
                    blacklisted_ips=blacklisted,
                    clean_ips=row[6],
                    blacklist_rate=rate,
                    last_scan_job_id=row[7],
                    last_scanned_at=row[8],
                )
                db.add(new_status)

        db.commit()
        logger.info("Refreshed block status for %d blocks", len(results))

    except Exception as e:
        logger.exception("Failed to refresh block status: %s", e)
    finally:
        db.close()
