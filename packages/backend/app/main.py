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
from app.db.init_data import seed_default_admin
from app.db.session import Base, SessionLocal, engine

logger = logging.getLogger(__name__)

# Tables managed by create_all (legacy, no schema prefix)
LEGACY_TABLES = {"users", "hostnames", "check_histories", "blacklisted_hostnames"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Only auto-create legacy tables (public schema).
    # blacklistify.* tables are managed by Alembic migrations.
    try:
        legacy_tables = [
            t for t in Base.metadata.sorted_tables
            if t.name in LEGACY_TABLES and t.schema is None
        ]
        Base.metadata.create_all(bind=engine, tables=legacy_tables)

        # Run Alembic migrations for blacklistify schema
        try:
            _run_alembic_upgrade()
        except Exception as e:
            logger.warning("Alembic migration skipped: %s", e)

        db = SessionLocal()
        try:
            seed_default_admin(db)
        finally:
            db.close()
    except Exception as e:
        # Don't crash the app if DB is temporarily unavailable.
        # Health check will still work, endpoints will fail gracefully.
        logger.error("Database initialization failed: %s", e)

    yield


def _run_alembic_upgrade():
    """Run alembic upgrade head on startup."""
    import os
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config()
    # Find alembic.ini relative to app directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(base_dir, "alembic.ini")

    if not os.path.exists(ini_path):
        logger.warning("alembic.ini not found at %s, skipping migrations", ini_path)
        return

    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied successfully")


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

    # Legacy routers (backward compatible)
    app.include_router(auth_router)
    app.include_router(blacklist_router)
    app.include_router(hostname_router)
    app.include_router(tools_router)

    # New v1 API routers
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
