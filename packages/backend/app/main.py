import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    auth_router,
    blacklist_router,
    hostname_router,
    tools_router,
    api_keys_router,
    webhooks_router,
    subnets_router,
    scans_router,
    dashboard_api_router,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Seed default admin user via Supabase client
    try:
        from app.db.client import db
        from app.core.security import hash_password

        existing = db.get_user_by_username(settings.default_admin_username)
        if not existing:
            db.create_user(
                username=settings.default_admin_username,
                email=settings.default_admin_email,
                phone=settings.default_admin_phone,
                hashed_password=hash_password(settings.default_admin_password),
                is_active=True,
                is_staff=True,
                is_superuser=True,
            )
            logger.info("Default admin user created: %s", settings.default_admin_username)
        else:
            logger.info("Admin user already exists: %s", settings.default_admin_username)
    except Exception as e:
        logger.error("Failed to seed admin user: %s", e)

    yield


def create_app() -> FastAPI:
    if not settings.app_debug and settings.app_secret_key == "insecure-dev-secret-key-change-me":
        raise RuntimeError("APP_SECRET_KEY must be set in non-debug environments")

    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        docs_url="/swagger/",
        redoc_url="/redoc/",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(blacklist_router)
    app.include_router(hostname_router)
    app.include_router(tools_router)
    app.include_router(api_keys_router)
    app.include_router(webhooks_router)
    app.include_router(subnets_router)
    app.include_router(scans_router)
    app.include_router(dashboard_api_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

    return app


app = create_app()
