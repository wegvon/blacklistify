"""
Individual subnet/batch scanning task.
Uses the async DNSBL engine for high-throughput checking.
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
    name="app.tasks.scan_subnet.scan_ip_batch",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def scan_ip_batch(
    self,
    job_id: int,
    subnet_id: str,
    subnet_cidr: str,
    ips: list[str],
    bypass_cache: bool = False,
):
    """
    Scan a batch of IPs against DNSBL providers.
    Results are written to scan_results table.
    """
    start_time = time.monotonic()
    db = SessionLocal()

    try:
        # Import async engine
        from app.services.dnsbl_async import AsyncDNSBLChecker

        cache = None if bypass_cache else RedisCache()
        checker = AsyncDNSBLChecker(cache=cache)

        # Run async check
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(checker.check_batch(ips))
        finally:
            loop.close()

        # Write results to DB
        blacklisted_count = 0
        for result in results:
            is_bl = result.get("is_blacklisted", False)
            if is_bl:
                blacklisted_count += 1

            scan_result = ScanResult(
                scan_job_id=job_id,
                subnet_id=subnet_id,
                subnet_cidr=subnet_cidr,
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

            # Check if job is complete
            if job.scanned_ips >= job.total_ips:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)

        db.commit()

        elapsed = time.monotonic() - start_time
        logger.info(
            "Batch scan: job=%d subnet=%s ips=%d blacklisted=%d time=%.1fs",
            job_id, subnet_cidr, len(ips), blacklisted_count, elapsed,
        )

        # Trigger alerts if blacklisted IPs found
        if blacklisted_count > 0:
            from app.tasks.notifications import check_and_send_alerts
            check_and_send_alerts.delay(
                job_id=job_id,
                subnet_id=subnet_id,
                subnet_cidr=subnet_cidr,
                blacklisted_count=blacklisted_count,
            )

    except Exception as e:
        logger.exception("Batch scan failed: job=%d subnet=%s error=%s", job_id, subnet_cidr, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # Mark job as failed if all retries exhausted
            job = db.query(ScanJob).filter_by(id=job_id).first()
            if job and job.status == "running":
                job.error_message = f"Batch failed after retries: {e}"
                db.commit()
    finally:
        db.close()
