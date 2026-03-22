from pydantic import BaseModel


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = ["read"]
    expires_in_days: int | None = None


class ApiKeyCreateResponse(BaseModel):
    id: int
    name: str
    key: str  # Only returned on creation, never stored
    key_prefix: str
    scopes: list[str]
    expires_at: str | None = None
    created_at: str


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: str | None = None
    expires_at: str | None = None
    created_at: str
