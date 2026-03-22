"""Webhook delivery and alert tasks — uses Supabase REST API."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from app.core.celery_app import celery
from app.db.client import db

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.notifications.check_and_send_alerts")
def check_and_send_alerts(job_id: int, block_id: str, block_cidr: str, blacklisted_count: int):
    try:
        rules = db.list_alert_rules(active_only=True)
        for rule in rules:
            if rule.get("subnet_filter") and rule["subnet_filter"] != block_cidr:
                continue

            should_fire = False
            if rule["condition_type"] == "blacklist_detected" and blacklisted_count > 0:
                should_fire = True
            elif rule["condition_type"] == "blacklist_rate_above" and rule.get("threshold"):
                status = db.get_block_status(block_id)
                if status and float(status.get("blacklist_rate", 0)) > float(rule["threshold"]):
                    should_fire = True

            if should_fire and rule.get("webhook_id"):
                webhook = db.get_webhook(rule["webhook_id"])
                if webhook and webhook.get("is_active"):
                    deliver_webhook.delay(
                        webhook_id=webhook["id"], event="blacklist.detected",
                        data={"block_id": block_id, "block_cidr": block_cidr, "blacklisted_count": blacklisted_count, "scan_job_id": job_id, "alert_rule": rule["name"]},
                    )
    except Exception as e:
        logger.exception("Alert check failed: %s", e)


@celery.task(bind=True, name="app.tasks.notifications.deliver_webhook", max_retries=5, default_retry_delay=30)
def deliver_webhook(self, webhook_id: int, event: str, data: dict):
    try:
        webhook = db.get_webhook(webhook_id)
        if not webhook or not webhook.get("is_active"):
            return

        payload = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), "data": data}
        body = json.dumps(payload, separators=(",", ":"))
        signature = hmac.new(webhook["secret"].encode(), body.encode(), hashlib.sha256).hexdigest()

        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook["url"], content=body, headers={
                "Content-Type": "application/json",
                "X-Blacklistify-Event": event,
                "X-Blacklistify-Signature": f"sha256={signature}",
            })
            response.raise_for_status()

        db.update_webhook(webhook_id, {"last_triggered_at": datetime.now(timezone.utc).isoformat(), "failure_count": 0})
        logger.info("Webhook delivered: id=%d event=%s", webhook_id, event)

    except httpx.HTTPStatusError as e:
        logger.warning("Webhook HTTP error: id=%d status=%d", webhook_id, e.response.status_code)
        webhook = db.get_webhook(webhook_id)
        if webhook:
            fc = (webhook.get("failure_count") or 0) + 1
            update = {"failure_count": fc}
            if fc >= 10:
                update["is_active"] = False
            db.update_webhook(webhook_id, update)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
    except Exception as e:
        logger.exception("Webhook failed: id=%d error=%s", webhook_id, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
