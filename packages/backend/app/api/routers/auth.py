from fastapi import APIRouter, HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.client import db
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserCreateRequest, UserResponse

router = APIRouter(prefix="/user", tags=["auth"])


@router.post("/create/", response_model=UserResponse)
def create_user(payload: UserCreateRequest):
    existing = db.get_user_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

    user = db.create_user(
        username=payload.username,
        email=payload.email,
        phone=payload.phone_number,
        hashed_password=hash_password(payload.password),
    )
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        phone_number=user.get("phone_number", ""),
    )


@router.post("/login/", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = db.get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return TokenResponse(
        access=create_access_token(user["username"]),
        refresh=create_refresh_token(user["username"]),
    )


@router.post("/token/refresh/", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest):
    decoded = decode_token(payload.refresh)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    subject = decoded.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenResponse(access=create_access_token(subject), refresh=create_refresh_token(subject))
