"""
Scan cycle orchestration tasks.
Manages sampling scans, full scans, and subnet status refresh.
"""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery
from app.db.session import SessionLocal
from app.db.supabase_read import subnet_reader
from app.models.scan_job import ScanJob
from app.models.subnet_status import SubnetStatus
from app.services.subnet_expander import sample_ips_from_cidr, cidr_to_ips, cidr_ip_count, split_into_batches
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="app.tasks.scan_cycle.run_sampling_scan")
def run_sampling_scan(self):
    """
    Sampling scan: pick representative IPs from each subnet.
    Runs every N hours (configured via SCAN_INTERVAL_HOURS).
    """
    db = SessionLocal()
    try:
        # 1. Create scan job
        job = ScanJob(
            job_type="sampling",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info("Starting sampling scan job #%d", job.id)

        # 2. Get active subnets from Ripefy
        try:
            subnets = subnet_reader.get_active_subnets()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed to read subnets: {e}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error("Sampling scan failed: %s", e)
            return

        if not subnets:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("No active subnets found, scan completed")
            return

        job.total_subnets = len(subnets)

        # 3. Build sample IP list
        all_tasks = []
        total_ips = 0
        for subnet in subnets:
            cidr = subnet.get("cidr", "")
            subnet_id = subnet.get("id", "")
            if not cidr:
                continue
            sample_ips = sample_ips_from_cidr(cidr)
            total_ips += len(sample_ips)

            # Split into batches
            batches = split_into_batches(sample_ips, settings.scan_batch_size)
            for batch in batches:
                all_tasks.append({
                    "job_id": job.id,
                    "subnet_id": subnet_id,
                    "subnet_cidr": cidr,
                    "ips": batch,
                })

        job.total_ips = total_ips
        db.commit()

        # 4. Dispatch batches to scan_subnet tasks
        from app.tasks.scan_subnet import scan_ip_batch
        for task_data in all_tasks:
            scan_ip_batch.delay(
                job_id=task_data["job_id"],
                subnet_id=task_data["subnet_id"],
                subnet_cidr=task_data["subnet_cidr"],
                ips=task_data["ips"],
            )

        logger.info(
            "Sampling scan job #%d: dispatched %d batches for %d IPs across %d subnets",
            job.id, len(all_tasks), total_ips, len(subnets),
        )

    except Exception as e:
        logger.exception("Sampling scan failed: %s", e)
    finally:
        db.close()


@celery.task(bind=True, name="app.tasks.scan_cycle.run_full_scan")
def run_full_scan(self):
    """
    Full scan: scan ALL IPs in ALL subnets.
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
            subnets = subnet_reader.get_active_subnets()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed to read subnets: {e}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        if not subnets:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        job.total_subnets = len(subnets)
        total_ips = 0
        all_tasks = []

        for subnet in subnets:
            cidr = subnet.get("cidr", "")
            subnet_id = subnet.get("id", "")
            if not cidr:
                continue
            ips = cidr_to_ips(cidr)
            total_ips += len(ips)

            batches = split_into_batches(ips, settings.scan_batch_size)
            for batch in batches:
                all_tasks.append({
                    "job_id": job.id,
                    "subnet_id": subnet_id,
                    "subnet_cidr": cidr,
                    "ips": batch,
                })

        job.total_ips = total_ips
        db.commit()

        from app.tasks.scan_subnet import scan_ip_batch
        for task_data in all_tasks:
            scan_ip_batch.delay(
                job_id=task_data["job_id"],
                subnet_id=task_data["subnet_id"],
                subnet_cidr=task_data["subnet_cidr"],
                ips=task_data["ips"],
                bypass_cache=True,
            )

        logger.info(
            "Full scan job #%d: dispatched %d batches for %d IPs across %d subnets",
            job.id, len(all_tasks), total_ips, len(subnets),
        )

    except Exception as e:
        logger.exception("Full scan failed: %s", e)
    finally:
        db.close()


@celery.task(name="app.tasks.scan_cycle.refresh_subnet_status")
def refresh_subnet_status():
    """
    Recalculate subnet_status from latest scan_results.
    Runs every 30 minutes.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import text

        # Get latest results per subnet, aggregated
        query = text("""
            WITH latest_results AS (
                SELECT DISTINCT ON (ip_address, subnet_cidr)
                    subnet_id,
                    subnet_cidr,
                    ip_address,
                    is_blacklisted,
                    providers_detected,
                    scan_job_id,
                    checked_at
                FROM blacklistify.scan_results
                ORDER BY ip_address, subnet_cidr, checked_at DESC
            )
            SELECT
                subnet_id,
                subnet_cidr,
                COUNT(*) as total_ips,
                COUNT(*) FILTER (WHERE is_blacklisted = TRUE) as blacklisted_ips,
                COUNT(*) FILTER (WHERE is_blacklisted = FALSE) as clean_ips,
                MAX(scan_job_id) as last_scan_job_id,
                MAX(checked_at) as last_scanned_at
            FROM latest_results
            WHERE subnet_id IS NOT NULL
            GROUP BY subnet_id, subnet_cidr
        """)

        results = db.execute(query).fetchall()

        for row in results:
            subnet_id = row[0]
            total = row[2]
            blacklisted = row[3]
            rate = round(blacklisted / total, 4) if total > 0 else 0

            existing = db.query(SubnetStatus).filter_by(subnet_id=subnet_id).first()
            if existing:
                old_blacklisted = existing.blacklisted_ips
                existing.total_ips = total
                existing.blacklisted_ips = blacklisted
                existing.clean_ips = row[4]
                existing.blacklist_rate = rate
                existing.last_scan_job_id = row[5]
                existing.last_scanned_at = row[6]
                if old_blacklisted != blacklisted:
                    existing.status_changed_at = datetime.now(timezone.utc)
            else:
                new_status = SubnetStatus(
                    subnet_id=subnet_id,
                    subnet_cidr=row[1],
                    total_ips=total,
                    blacklisted_ips=blacklisted,
                    clean_ips=row[4],
                    blacklist_rate=rate,
                    last_scan_job_id=row[5],
                    last_scanned_at=row[6],
                )
                db.add(new_status)

        db.commit()
        logger.info("Refreshed subnet status for %d subnets", len(results))

    except Exception as e:
        logger.exception("Failed to refresh subnet status: %s", e)
    finally:
        db.close()
