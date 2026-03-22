from app.api.routers.auth import router as auth_router
from app.api.routers.blacklist import router as blacklist_router
from app.api.routers.hostname import router as hostname_router
from app.api.routers.tools import router as tools_router

# New v1 routers
from app.api.routers.api_keys import router as api_keys_router
from app.api.routers.webhooks import router as webhooks_router
from app.api.routers.subnets import router as subnets_router
from app.api.routers.scans import router as scans_router
from app.api.routers.dashboard_api import router as dashboard_api_router

__all__ = [
    "auth_router",
    "blacklist_router",
    "hostname_router",
    "tools_router",
    "api_keys_router",
    "webhooks_router",
    "subnets_router",
    "scans_router",
    "dashboard_api_router",
]
