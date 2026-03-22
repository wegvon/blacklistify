"""Cleanup tasks — uses Supabase REST API."""

import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery
from app.db.client import db

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.cleanup.purge_old_results")
def purge_old_results(retention_days: int = 30):
    """Remove scan results older than retention_days."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

        # Delete old results via Supabase
        db.client.table("blf_scan_results").delete().lt("checked_at", cutoff).execute()

        # Delete orphaned completed/failed jobs
        db.client.table("blf_scan_jobs").delete().in_("status", ["completed", "failed"]).lt("created_at", cutoff).execute()

        logger.info("Cleanup: purged results older than %d days", retention_days)

    except Exception as e:
        logger.exception("Cleanup failed: %s", e)
