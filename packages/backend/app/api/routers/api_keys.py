"""API Key management endpoints."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, hash_password
from app.db.client import db
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

VALID_SCOPES = {"read", "write", "scan"}


def _generate_api_key() -> tuple[str, str]:
    random_part = secrets.token_hex(24)
    full_key = f"blf_k1_{random_part}"
    prefix = full_key[:8]
    return full_key, prefix


@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(body: ApiKeyCreateRequest, user: dict = Depends(get_current_user)):
    invalid = set(body.scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(400, f"Invalid scopes: {invalid}. Valid: {VALID_SCOPES}")

    full_key, prefix = _generate_api_key()
    key_hash = hash_password(full_key)
    expires_at = None
    if body.expires_in_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()

    record = db.create_api_key({
        "key_prefix": prefix,
        "key_hash": key_hash,
        "name": body.name,
        "scopes": body.scopes,
        "expires_at": expires_at,
    })

    return ApiKeyCreateResponse(
        id=record["id"],
        name=record["name"],
        key=full_key,
        key_prefix=prefix,
        scopes=record.get("scopes", ["read"]),
        expires_at=expires_at,
        created_at=record["created_at"],
    )


@router.get("/", response_model=list[ApiKeyResponse])
def list_api_keys(user: dict = Depends(get_current_user)):
    keys = db.list_api_keys()
    return [
        ApiKeyResponse(
            id=k["id"], name=k["name"], key_prefix=k["key_prefix"],
            scopes=k.get("scopes", ["read"]), is_active=k.get("is_active", True),
            last_used_at=k.get("last_used_at"), expires_at=k.get("expires_at"),
            created_at=k["created_at"],
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: int, user: dict = Depends(get_current_user)):
    db.deactivate_api_key(key_id)
