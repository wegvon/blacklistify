"""Webhook and alert rule management endpoints."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.client import db
from app.schemas.webhook import (
    AlertRuleCreateRequest, AlertRuleResponse,
    WebhookCreateRequest, WebhookResponse, WebhookTestResponse,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

VALID_EVENTS = {"blacklist.detected", "blacklist.resolved", "scan.completed", "scan.failed", "alert.threshold"}


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(body: WebhookCreateRequest, user: dict = Depends(get_current_user)):
    invalid = set(body.events) - VALID_EVENTS
    if invalid:
        raise HTTPException(400, f"Invalid events: {invalid}")

    record = db.create_webhook({
        "url": body.url,
        "events": body.events,
        "secret": secrets.token_hex(32),
    })
    return WebhookResponse(
        id=record["id"], url=record["url"], events=record["events"],
        is_active=record.get("is_active", True), last_triggered_at=None,
        failure_count=0, created_at=record["created_at"],
    )


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(user: dict = Depends(get_current_user)):
    webhooks = db.list_webhooks()
    return [
        WebhookResponse(
            id=w["id"], url=w["url"], events=w.get("events", []),
            is_active=w.get("is_active", True),
            last_triggered_at=w.get("last_triggered_at"),
            failure_count=w.get("failure_count", 0),
            created_at=w["created_at"],
        )
        for w in webhooks
    ]


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: int, user: dict = Depends(get_current_user)):
    db.delete_webhook(webhook_id)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook(webhook_id: int, user: dict = Depends(get_current_user)):
    webhook = db.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(404, "Webhook not found")

    payload = {
        "event": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "Test webhook from Blacklistify"},
    }
    body = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(webhook["secret"].encode(), body.encode(), hashlib.sha256).hexdigest()

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook["url"], content=body, headers={
                "Content-Type": "application/json",
                "X-Blacklistify-Event": "test",
                "X-Blacklistify-Signature": f"sha256={signature}",
            })
        return WebhookTestResponse(success=response.is_success, status_code=response.status_code)
    except Exception as e:
        return WebhookTestResponse(success=False, error=str(e))


# Alert Rules
@router.post("/alerts/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(body: AlertRuleCreateRequest, user: dict = Depends(get_current_user)):
    webhook = db.get_webhook(body.webhook_id)
    if not webhook:
        raise HTTPException(400, "Webhook not found")

    record = db.create_alert_rule({
        "name": body.name,
        "condition_type": body.condition_type,
        "threshold": float(body.threshold) if body.threshold else None,
        "subnet_filter": body.subnet_filter,
        "webhook_id": body.webhook_id,
    })
    return AlertRuleResponse(
        id=record["id"], name=record["name"],
        condition_type=record["condition_type"],
        threshold=record.get("threshold"),
        subnet_filter=record.get("subnet_filter"),
        webhook_id=record.get("webhook_id"),
        is_active=record.get("is_active", True),
        created_at=record["created_at"],
    )


@router.get("/alerts/", response_model=list[AlertRuleResponse])
def list_alert_rules(user: dict = Depends(get_current_user)):
    rules = db.list_alert_rules()
    return [
        AlertRuleResponse(
            id=r["id"], name=r["name"], condition_type=r["condition_type"],
            threshold=r.get("threshold"), subnet_filter=r.get("subnet_filter"),
            webhook_id=r.get("webhook_id"), is_active=r.get("is_active", True),
            created_at=r["created_at"],
        )
        for r in rules
    ]


@router.delete("/alerts/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(rule_id: int, user: dict = Depends(get_current_user)):
    db.delete_alert_rule(rule_id)
