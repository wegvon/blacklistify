# Architecture

**Analysis Date:** 2026-03-25

## Pattern Overview

**Overall:** Layered Monolith with Background Task Processing

**Key Characteristics:**
- FastAPI REST API as the core service
- Supabase REST API for all database operations (not direct SQL)
- Celery workers for async task processing (scanning, notifications)
- Redis as message broker between API and workers
- React SPA frontend consuming the API
- Docker-based deployment with docker-compose

## Layers

**API Layer (FastAPI):**
- Purpose: HTTP request handling, validation, authentication, routing
- Location: `packages/backend/app/api/routers/`
- Contains: Route handlers for auth, blacklist, scans, subnets, webhooks, etc.
- Depends on: Services layer, DB client
- Used by: Frontend, external API consumers

**Services Layer:**
- Purpose: Business logic, external API integrations
- Location: `packages/backend/app/services/`
- Contains: DNSBL checking, WHOIS lookup, AbuseIPDB, server status, cache
- Depends on: DB client, external APIs
- Used by: API routers, task workers

**Data Access Layer (Supabase Wrapper):**
- Purpose: Unified database operations via Supabase REST API
- Location: `packages/backend/app/db/client.py`
- Contains: `SupabaseDB` class with CRUD operations for all tables
- Depends on: Supabase Python client
- Used by: API routers, services, tasks

**Task Queue Layer (Celery):**
- Purpose: Async task processing (periodic scans, notifications)
- Location: `packages/backend/app/tasks/`
- Contains: `scan_cycle.py`, `scan_subnet.py`, `notifications.py`, `cleanup.py`
- Depends on: Redis broker, services, DB client
- Used by: Celery beat scheduler, API triggers

**Core Layer:**
- Purpose: Shared utilities, config, security
- Location: `packages/backend/app/core/`
- Contains: Config settings, security utilities, Celery app
- Depends on: Environment variables
- Used by: All layers

**Frontend Layer (React SPA):**
- Purpose: UI rendering, client-side routing, API consumption
- Location: `packages/frontend/src/`
- Contains: Pages, components, services, routes
- Depends on: Backend API
- Used by: End users via browser

## Data Flow

**Authentication Flow:**
1. User submits credentials to `/api/auth/login`
2. Backend validates, creates JWT access + refresh tokens
3. Frontend stores tokens (likely in localStorage/sessionStorage)
4. Subsequent requests include `Authorization: Bearer <token>`
5. Backend validates JWT via `security.py` dependency

**Scan Request Flow:**
1. User triggers scan via frontend
2. Frontend POSTs to `/api/scans/` or `/api/blacklist/check`
3. API creates scan job record in Supabase
4. API queues Celery task for async processing
5. Worker picks up task, performs DNSBL checks
6. Results stored in Supabase via DB client
7. If webhook configured, worker triggers notification

**Webhook Notification Flow:**
1. Celery worker completes scan cycle
2. Worker calls `notifications.py` to evaluate alert rules
3. For matching rules, `webhooks.py` sends POST to configured URL
4. Delivery attempted async via httpx

**State Management:**
- Frontend: React Context + local state (Mantine hooks)
- Backend: Stateless (JWT tokens), Supabase for persistence
- Workers: Stateless, results stored in Supabase

## Key Abstractions

**SupabaseDB (Database Client):**
- Purpose: Single interface for all DB operations
- Examples: `packages/backend/app/db/client.py`
- Pattern: Repository pattern wrapping Supabase REST client

**Scan Job Processing:**
- Purpose: Encapsulate multi-IP scanning logic
- Examples: `packages/backend/app/services/dnsbl_async.py`, `packages/backend/app/tasks/scan_cycle.py`
- Pattern: Async iteration with concurrency control

**Settings (Configuration):**
- Purpose: Type-safe configuration access
- Examples: `packages/backend/app/core/config.py`
- Pattern: Dataclass-based settings with env var parsing

## Entry Points

**Backend API:**
- Location: `packages/backend/app/main.py` (`create_app()`)
- Triggers: Uvicorn ASGI server, Docker container
- Responsibilities: HTTP middleware, router registration, lifespan events (admin seeding)

**Celery Worker:**
- Location: `packages/backend/app/core/celery_app.py`
- Triggers: `celery -A app.core.celery_app worker` command
- Responsibilities: Task execution, result storage

**Celery Beat (Scheduler):**
- Triggers: `celery -A app.core.celery_app beat` command
- Responsibilities: Periodic task scheduling (scan cycles)

**Frontend Dev Server:**
- Location: `packages/frontend/` (Vite)
- Triggers: `yarn dev` or `npm run dev`
- Responsibilities: Dev server, HMR, proxy to backend

**Frontend Prod Build:**
- Triggers: `yarn build` or `npm run build`
- Responsibilities: Production bundle, static file generation

## Error Handling

**Strategy:** Exception propagation with FastAPI exception handlers

**Patterns:**
- FastAPI HTTP exceptions for request-level errors
- Try/except blocks in services for external API failures
- Celery retry mechanism for transient failures (not observed in code)
- Logging via Python `logging` module

## Cross-Cutting Concerns

**Logging:** Python standard logging (`logging.getLogger(__name__)`)

**Validation:** Pydantic models for request/response validation (`packages/backend/app/schemas/`)

**Authentication:** JWT Bearer tokens, `security.py` password hashing with passlib

**CORS:** FastAPI CORSMiddleware, configurable origins

---

*Architecture analysis: 2026-03-25*
