"""
Block-level scanning task.
Uses the async DNSBL engine for high-throughput checking.

Each task receives a batch of IPs with their corresponding block metadata.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.core.celery_app import celery
from app.db.session import SessionLocal
from app.models.scan_job import ScanJob
from app.models.scan_result import ScanResult
from app.services.cache import RedisCache

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="app.tasks.scan_subnet.scan_block_batch",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def scan_block_batch(
    self,
    job_id: int,
    ips: list[str],
    blocks: list[dict],
    bypass_cache: bool = False,
):
    """
    Scan a batch of IPs against DNSBL providers.

    Args:
        job_id: ScanJob ID
        ips: List of IP addresses to check
        blocks: List of block metadata dicts (block_id, block_cidr, prefix_id, prefix_cidr)
               Same length as ips — each IP maps to its block.
        bypass_cache: Skip Redis cache (for full scans)
    """
    start_time = time.monotonic()
    db = SessionLocal()

    try:
        from app.services.dnsbl_async import AsyncDNSBLChecker

        cache = None if bypass_cache else RedisCache()
        checker = AsyncDNSBLChecker(cache=cache)

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(checker.check_batch(ips))
        finally:
            loop.close()

        blacklisted_count = 0
        for i, result in enumerate(results):
            is_bl = result.get("is_blacklisted", False)
            if is_bl:
                blacklisted_count += 1

            block = blocks[i] if i < len(blocks) else blocks[0]

            scan_result = ScanResult(
                scan_job_id=job_id,
                block_id=block.get("block_id"),
                block_cidr=block.get("block_cidr", ""),
                prefix_id=block.get("prefix_id"),
                prefix_cidr=block.get("prefix_cidr"),
                ip_address=result["ip"],
                is_blacklisted=is_bl,
                providers_detected=result.get("providers_detected", []),
                providers_total=result.get("providers_total", 0),
            )
            db.add(scan_result)

        # Update job counters
        job = db.query(ScanJob).filter_by(id=job_id).first()
        if job:
            job.scanned_ips = (job.scanned_ips or 0) + len(ips)
            job.blacklisted_ips = (job.blacklisted_ips or 0) + blacklisted_count

            if job.scanned_ips >= job.total_ips:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)

        db.commit()

        elapsed = time.monotonic() - start_time
        block_cidrs = set(b.get("block_cidr", "") for b in blocks)
        logger.info(
            "Batch scan: job=%d blocks=%s ips=%d blacklisted=%d time=%.1fs",
            job_id, block_cidrs, len(ips), blacklisted_count, elapsed,
        )

        if blacklisted_count > 0:
            from app.tasks.notifications import check_and_send_alerts
            # Send alert for each unique block that had blacklisted IPs
            for block_cidr in block_cidrs:
                matching_block = next((b for b in blocks if b.get("block_cidr") == block_cidr), blocks[0])
                check_and_send_alerts.delay(
                    job_id=job_id,
                    block_id=matching_block.get("block_id", ""),
                    block_cidr=block_cidr,
                    blacklisted_count=blacklisted_count,
                )

    except Exception as e:
        logger.exception("Batch scan failed: job=%d error=%s", job_id, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            job = db.query(ScanJob).filter_by(id=job_id).first()
            if job and job.status == "running":
                job.error_message = f"Batch failed after retries: {e}"
                db.commit()
    finally:
        db.close()
