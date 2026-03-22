"""
Webhook delivery and alert notification tasks.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from app.core.celery_app import celery
from app.db.session import SessionLocal
from app.models.alert_rule import AlertRule
from app.models.subnet_status import SubnetStatus
from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.notifications.check_and_send_alerts")
def check_and_send_alerts(
    job_id: int,
    subnet_id: str,
    subnet_cidr: str,
    blacklisted_count: int,
):
    """Check alert rules and dispatch webhook notifications."""
    db = SessionLocal()
    try:
        # Get active alert rules
        rules = db.query(AlertRule).filter_by(is_active=True).all()

        for rule in rules:
            # Check subnet filter
            if rule.subnet_filter and rule.subnet_filter != subnet_cidr:
                continue

            should_fire = False

            if rule.condition_type == "blacklist_detected" and blacklisted_count > 0:
                should_fire = True

            elif rule.condition_type == "blacklist_rate_above" and rule.threshold:
                status = db.query(SubnetStatus).filter_by(subnet_id=subnet_id).first()
                if status and float(status.blacklist_rate) > float(rule.threshold):
                    should_fire = True

            if should_fire and rule.webhook_id:
                webhook = db.query(Webhook).filter_by(id=rule.webhook_id, is_active=True).first()
                if webhook:
                    deliver_webhook.delay(
                        webhook_id=webhook.id,
                        event="blacklist.detected",
                        data={
                            "subnet_id": subnet_id,
                            "subnet_cidr": subnet_cidr,
                            "blacklisted_count": blacklisted_count,
                            "scan_job_id": job_id,
                            "alert_rule": rule.name,
                        },
                    )

    except Exception as e:
        logger.exception("Alert check failed: %s", e)
    finally:
        db.close()


@celery.task(
    bind=True,
    name="app.tasks.notifications.deliver_webhook",
    max_retries=5,
    default_retry_delay=30,
)
def deliver_webhook(self, webhook_id: int, event: str, data: dict):
    """Deliver a webhook with HMAC-SHA256 signature."""
    db = SessionLocal()
    try:
        webhook = db.query(Webhook).filter_by(id=webhook_id).first()
        if not webhook or not webhook.is_active:
            return

        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        body = json.dumps(payload, separators=(",", ":"))

        # HMAC-SHA256 signature
        signature = hmac.new(
            webhook.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Blacklistify-Event": event,
            "X-Blacklistify-Signature": f"sha256={signature}",
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook.url, content=body, headers=headers)
            response.raise_for_status()

        # Success: reset failure count
        webhook.last_triggered_at = datetime.now(timezone.utc)
        webhook.failure_count = 0
        db.commit()

        logger.info("Webhook delivered: id=%d event=%s url=%s", webhook_id, event, webhook.url)

    except httpx.HTTPStatusError as e:
        logger.warning("Webhook HTTP error: id=%d status=%d", webhook_id, e.response.status_code)
        webhook = db.query(Webhook).filter_by(id=webhook_id).first()
        if webhook:
            webhook.failure_count += 1
            if webhook.failure_count >= 10:
                webhook.is_active = False
                logger.warning("Webhook disabled after 10 failures: id=%d", webhook_id)
            db.commit()
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass

    except Exception as e:
        logger.exception("Webhook delivery failed: id=%d error=%s", webhook_id, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
    finally:
        db.close()
