"""Block-level scanning task — uses Supabase REST API for all DB ops."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.core.celery_app import celery
from app.db.client import db
from app.services.cache import RedisCache

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="app.tasks.scan_subnet.scan_block_batch", max_retries=2, default_retry_delay=60, acks_late=True)
def scan_block_batch(self, job_id: int, ips: list[str], blocks: list[dict], bypass_cache: bool = False):
    start_time = time.monotonic()

    try:
        from app.services.dnsbl_async import AsyncDNSBLChecker

        cache = None if bypass_cache else RedisCache()
        checker = AsyncDNSBLChecker(cache=cache)

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(checker.check_batch(ips))
        finally:
            loop.close()

        # Build rows for batch insert
        rows = []
        blacklisted_count = 0
        for i, result in enumerate(results):
            is_bl = result.get("is_blacklisted", False)
            if is_bl:
                blacklisted_count += 1

            block = blocks[i] if i < len(blocks) else blocks[0]
            rows.append({
                "scan_job_id": job_id,
                "block_id": block.get("block_id"),
                "block_cidr": block.get("block_cidr", ""),
                "prefix_id": block.get("prefix_id"),
                "prefix_cidr": block.get("prefix_cidr"),
                "ip_address": result["ip"],
                "is_blacklisted": is_bl,
                "providers_detected": result.get("providers_detected", []),
                "providers_total": result.get("providers_total", 0),
            })

        # Batch insert results
        if rows:
            db.insert_scan_results(rows)

        # Update job counters
        job = db.get_scan_job(job_id)
        if job:
            new_scanned = (job.get("scanned_ips") or 0) + len(ips)
            new_bl = (job.get("blacklisted_ips") or 0) + blacklisted_count
            update = {"scanned_ips": new_scanned, "blacklisted_ips": new_bl}
            if new_scanned >= (job.get("total_ips") or 0):
                update["status"] = "completed"
                update["completed_at"] = datetime.now(timezone.utc).isoformat()
            db.update_scan_job(job_id, update)

        elapsed = time.monotonic() - start_time
        logger.info("Batch: job=%d ips=%d blacklisted=%d time=%.1fs", job_id, len(ips), blacklisted_count, elapsed)

        if blacklisted_count > 0:
            from app.tasks.notifications import check_and_send_alerts
            block_cidrs = set(b.get("block_cidr", "") for b in blocks)
            for cidr in block_cidrs:
                matching = next((b for b in blocks if b.get("block_cidr") == cidr), blocks[0])
                check_and_send_alerts.delay(job_id=job_id, block_id=matching.get("block_id", ""), block_cidr=cidr, blacklisted_count=blacklisted_count)

    except Exception as e:
        logger.exception("Batch failed: job=%d error=%s", job_id, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
