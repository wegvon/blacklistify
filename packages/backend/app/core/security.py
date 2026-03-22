from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User


# Use PBKDF2-SHA256 to avoid bcrypt backend/runtime incompatibilities in minimal containers.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _build_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _build_token(subject, "access", timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(subject: str) -> str:
    return _build_token(subject, "refresh", timedelta(days=settings.refresh_token_days))


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthError("Invalid token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise AuthError("Not authenticated")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise AuthError("Invalid token type")

    username = payload.get("sub")
    if not username:
        raise AuthError("Invalid token payload")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise AuthError("User not found")
    if not user.is_active:
        raise AuthError("User is inactive")

    return user


# ---------------------------------------------------------------------------
# API Key authentication
# ---------------------------------------------------------------------------

def _validate_api_key(api_key: str, db: Session):
    """Validate an API key and return the ApiKey record."""
    from app.models.api_key import ApiKey

    if not api_key or not api_key.startswith("blf_"):
        raise AuthError("Invalid API key format")

    prefix = api_key[:8]
    key_record = db.query(ApiKey).filter(
        ApiKey.key_prefix == prefix,
        ApiKey.is_active == True,
    ).first()

    if not key_record:
        raise AuthError("Invalid API key")

    # Verify hash
    if not pwd_context.verify(api_key, key_record.key_hash):
        raise AuthError("Invalid API key")

    # Check expiry
    if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
        raise AuthError("API key expired")

    # Update last_used_at
    key_record.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return key_record


class AuthContext:
    """Unified auth context for JWT or API key authentication."""

    def __init__(self, auth_type: str, user: User | None = None, api_key: Any = None):
        self.auth_type = auth_type  # "jwt" or "api_key"
        self.user = user
        self.api_key = api_key

    @property
    def scopes(self) -> list[str]:
        if self.auth_type == "jwt":
            return ["read", "write", "scan", "admin"]
        if self.api_key:
            return self.api_key.scopes or ["read"]
        return []

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> AuthContext:
    """
    Authenticate via JWT Bearer token OR X-API-Key header.
    JWT takes priority if both are provided.
    """
    # Try JWT first
    if credentials:
        try:
            user = get_current_user.__wrapped__(credentials, db) if hasattr(get_current_user, '__wrapped__') else None
        except Exception:
            user = None

        if user is None:
            payload = decode_token(credentials.credentials)
            if payload.get("type") != "access":
                raise AuthError("Invalid token type")
            username = payload.get("sub")
            if not username:
                raise AuthError("Invalid token payload")
            user = db.query(User).filter(User.username == username).first()
            if not user or not user.is_active:
                raise AuthError("User not found or inactive")

        return AuthContext(auth_type="jwt", user=user)

    # Try API key
    if x_api_key:
        key_record = _validate_api_key(x_api_key, db)
        return AuthContext(auth_type="api_key", api_key=key_record)

    raise AuthError("Authentication required. Provide Bearer token or X-API-Key header.")


def require_scope(scope: str):
    """Dependency factory that checks for a specific scope."""
    def checker(auth: AuthContext = Depends(get_auth_context)):
        if not auth.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {scope}",
            )
        return auth
    return checker
