from pydantic import BaseModel, HttpUrl


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str]  # ["blacklist.detected", "scan.completed", ...]


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    is_active: bool
    last_triggered_at: str | None = None
    failure_count: int = 0
    created_at: str


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: int | None = None
    error: str | None = None


class AlertRuleCreateRequest(BaseModel):
    name: str
    condition_type: str  # blacklist_detected, blacklist_rate_above, scan_failed
    threshold: float | None = None
    subnet_filter: str | None = None
    webhook_id: int


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    condition_type: str
    threshold: float | None = None
    subnet_filter: str | None = None
    webhook_id: int | None = None
    is_active: bool
    created_at: str
