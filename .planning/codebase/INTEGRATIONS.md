# External Integrations

**Analysis Date:** 2026-03-25

## APIs & External Services

**Supabase (Backend-as-a-Service):**
- What it's used for: All database operations (users, scan jobs, results, webhooks, API keys, alert rules)
- SDK/Client: `supabase` Python package v2.11.0
- Auth: `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` environment variables
- Implementation: REST API via Supabase client (NOT direct PostgreSQL)
- Tables: `blf_users`, `blf_hostnames`, `blf_scan_jobs`, `blf_scan_results`, `blf_block_status`, `blf_api_keys`, `blf_webhooks`, `blf_alert_rules`
- Note: Also reads READ-ONLY from Ripefy tables (`ip_prefixes`, `ip_blocks`, `customers`)

**AbuseIPDB (Threat Intelligence):**
- What it's used for: IP blacklist checking and abuse reporting
- SDK/Client: Custom implementation in `packages/backend/app/services/abuseipdb.py`
- Auth: `ABUSEIPDB_API_KEY` environment variable
- Endpoint: AbuseIPDB API v2

**DNSBL (DNS-based Blackhole List):**
- What it's used for: Checking if IPs are blacklisted on DNS-based blocklists
- SDK/Client: Custom async implementation in `packages/backend/app/services/dnsbl_async.py`
- Auth: None required (UDP/TCP DNS queries)
- Multiple DNSBL servers supported

## Data Storage

**PostgreSQL (via Supabase REST):**
- Type/Provider: Supabase hosted PostgreSQL
- Connection: `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
- Client: `supabase` Python client (REST API, not direct SQL)
- Note: SQLite fallback exists (`sqlite:///./app.db`) but not actively used

**Redis:**
- Type/Provider: Containerized Redis 7 Alpine
- Connection: `REDIS_URL` env var (default: `redis://localhost:6379/0`)
- Used for: Celery task queue broker and result backend
- Volume: `redisdata` Docker volume for persistence

**File Storage:**
- Local filesystem only (no S3/cloud storage)
- Scan results stored in Supabase
- Static assets in `packages/frontend/public/`

**Caching:**
- Custom cache implementation in `packages/backend/app/services/cache.py`
- TTL-based in-memory/file cache for scan results
- `SCAN_CACHE_TTL_HOURS` config (default: 6 hours)

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based authentication
- Implementation: `packages/backend/app/core/security.py`
- Token type: JWT (HS256 algorithm)
- Access token expiry: `ACCESS_TOKEN_MINUTES` (default: 30)
- Refresh token expiry: `REFRESH_TOKEN_DAYS` (default: 14)
- User stored in Supabase `blf_users` table

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Rollbar, etc.)

**Logs:**
- Python standard logging (`logging.getLogger()`)
- Uvicorn access logs (via ASGI)
- Output to stdout/stderr (Docker containers)
- No structured logging (JSON) detected

## CI/CD & Deployment

**Hosting:**
- Docker-based deployment (self-hosted)
- Docker Compose for orchestration
- Multi-container: backend, frontend, worker, beat, redis

**CI Pipeline:**
- GitHub Actions workflows in `.github/workflows/`
- No third-party CI services detected

## Environment Configuration

**Required env vars:**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `APP_SECRET_KEY` - JWT signing key (must be changed in production)
- `REDIS_URL` - Redis connection URL
- `CELERY_BROKER_URL` - Celery broker URL
- `CELERY_RESULT_BACKEND` - Celery result backend URL
- `ABUSEIPDB_API_KEY` - AbuseIPDB API key (optional)
- `APP_DEBUG` - Debug mode flag
- `APP_CORS_ALLOWED_ORIGINS` - CORS origins (comma-separated)

**Secrets location:**
- Environment variables (passed via `.env` file or Docker secrets)
- Default credentials hardcoded in `config.py` for development:
  - `DEFAULT_ADMIN_USERNAME=admin`
  - `DEFAULT_ADMIN_PASSWORD=password123`
  - `APP_SECRET_KEY=insecure-dev-secret-key-change-me`

## Webhooks & Callbacks

**Outgoing:**
- User-configurable webhooks for alerts
- Endpoint: `POST` to user-specified URL
- Implementation: `packages/backend/app/api/routers/webhooks.py`
- Delivery: Async via httpx
- Events: Alert triggers based on scan results

**Incoming:**
- None detected (no webhook receivers)

---

*Integration audit: 2026-03-25*
