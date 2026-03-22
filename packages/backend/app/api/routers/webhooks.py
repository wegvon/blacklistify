"""Webhook and alert rule management endpoints."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.alert_rule import AlertRule
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas.webhook import (
    AlertRuleCreateRequest,
    AlertRuleResponse,
    WebhookCreateRequest,
    WebhookResponse,
    WebhookTestResponse,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

VALID_EVENTS = {
    "blacklist.detected",
    "blacklist.resolved",
    "scan.completed",
    "scan.failed",
    "alert.threshold",
}


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invalid = set(body.events) - VALID_EVENTS
    if invalid:
        raise HTTPException(400, f"Invalid events: {invalid}. Valid: {VALID_EVENTS}")

    secret = secrets.token_hex(32)
    webhook = Webhook(
        url=body.url,
        events=body.events,
        secret=secret,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        last_triggered_at=None,
        failure_count=0,
        created_at=webhook.created_at.isoformat(),
    )


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    webhooks = db.query(Webhook).all()
    return [
        WebhookResponse(
            id=w.id,
            url=w.url,
            events=w.events,
            is_active=w.is_active,
            last_triggered_at=w.last_triggered_at.isoformat() if w.last_triggered_at else None,
            failure_count=w.failure_count,
            created_at=w.created_at.isoformat(),
        )
        for w in webhooks
    ]


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    webhook = db.query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    db.delete(webhook)
    db.commit()


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a test event to a webhook."""
    webhook = db.query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")

    payload = {
        "event": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "This is a test webhook from Blacklistify"},
    }
    body = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(webhook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                webhook.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Blacklistify-Event": "test",
                    "X-Blacklistify-Signature": f"sha256={signature}",
                },
            )
        return WebhookTestResponse(success=response.is_success, status_code=response.status_code)
    except Exception as e:
        return WebhookTestResponse(success=False, error=str(e))


# ---------------------------------------------------------------------------
# Alert Rules
# ---------------------------------------------------------------------------

@router.post("/alerts/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    body: AlertRuleCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    webhook = db.query(Webhook).filter_by(id=body.webhook_id).first()
    if not webhook:
        raise HTTPException(400, "Webhook not found")

    rule = AlertRule(
        name=body.name,
        condition_type=body.condition_type,
        threshold=body.threshold,
        subnet_filter=body.subnet_filter,
        webhook_id=body.webhook_id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        condition_type=rule.condition_type,
        threshold=float(rule.threshold) if rule.threshold else None,
        subnet_filter=rule.subnet_filter,
        webhook_id=rule.webhook_id,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
    )


@router.get("/alerts/", response_model=list[AlertRuleResponse])
def list_alert_rules(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = db.query(AlertRule).all()
    return [
        AlertRuleResponse(
            id=r.id,
            name=r.name,
            condition_type=r.condition_type,
            threshold=float(r.threshold) if r.threshold else None,
            subnet_filter=r.subnet_filter,
            webhook_id=r.webhook_id,
            is_active=r.is_active,
            created_at=r.created_at.isoformat(),
        )
        for r in rules
    ]


@router.delete("/alerts/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rule = db.query(AlertRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    db.delete(rule)
    db.commit()
