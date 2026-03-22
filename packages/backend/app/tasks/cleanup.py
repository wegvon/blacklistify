"""
Cleanup tasks for old scan data.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.celery_app import celery
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.cleanup.purge_old_results")
def purge_old_results(retention_days: int = 30):
    """
    Remove scan results older than retention_days.
    Keeps the latest result per IP to preserve current state.
    Runs daily at 03:00.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # Delete old results but keep latest per IP
        query = text("""
            DELETE FROM blacklistify.scan_results
            WHERE id NOT IN (
                SELECT DISTINCT ON (ip_address, subnet_cidr) id
                FROM blacklistify.scan_results
                ORDER BY ip_address, subnet_cidr, checked_at DESC
            )
            AND checked_at < :cutoff
        """)

        result = db.execute(query, {"cutoff": cutoff})
        deleted = result.rowcount
        db.commit()

        # Also clean up completed/failed jobs older than retention
        job_query = text("""
            DELETE FROM blacklistify.scan_jobs
            WHERE status IN ('completed', 'failed')
            AND created_at < :cutoff
            AND id NOT IN (
                SELECT DISTINCT scan_job_id FROM blacklistify.scan_results
            )
        """)
        job_result = db.execute(job_query, {"cutoff": cutoff})
        jobs_deleted = job_result.rowcount
        db.commit()

        logger.info(
            "Cleanup: deleted %d old results and %d orphaned jobs (retention=%d days)",
            deleted, jobs_deleted, retention_days,
        )

    except Exception as e:
        logger.exception("Cleanup failed: %s", e)
    finally:
        db.close()
