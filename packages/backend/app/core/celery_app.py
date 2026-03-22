from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery = Celery("blacklistify")

celery.config_from_object({
    "broker_url": settings.celery_broker_url,
    "result_backend": settings.celery_result_backend,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "task_routes": {
        "app.tasks.scan_cycle.*": {"queue": "scans"},
        "app.tasks.scan_subnet.*": {"queue": "scans"},
        "app.tasks.notifications.*": {"queue": "default"},
        "app.tasks.cleanup.*": {"queue": "default"},
    },
    "beat_schedule": {
        "sampling-scan": {
            "task": "app.tasks.scan_cycle.run_sampling_scan",
            "schedule": crontab(minute=0, hour=f"*/{settings.scan_interval_hours}"),
        },
        "full-scan-weekly": {
            "task": "app.tasks.scan_cycle.run_full_scan",
            "schedule": crontab(minute=0, hour=2, day_of_week=0),  # Sunday 02:00
        },
        "cleanup-old-results": {
            "task": "app.tasks.cleanup.purge_old_results",
            "schedule": crontab(minute=0, hour=3),  # Daily 03:00
        },
        "refresh-subnet-status": {
            "task": "app.tasks.scan_cycle.refresh_subnet_status",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
    },
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "task_reject_on_worker_lost": True,
})

celery.autodiscover_tasks(["app.tasks"])
