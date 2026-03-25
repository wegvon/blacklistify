# Codebase Concerns

**Analysis Date:** 2026-03-25

## Tech Debt

**Database Abstraction Mismatch:**
- Issue: SQLAlchemy models exist (`packages/backend/app/models/`) but are not used; all DB operations go through Supabase REST API
- Files: `packages/backend/app/models/__init__.py`, `packages/backend/app/db/client.py`
- Impact: Maintenance confusion, unused code, potential for model/API drift
- Fix approach: Remove SQLAlchemy models if not needed, or use them with Supabase

**Configuration Default Credentials:**
- Issue: Default admin password and secret key hardcoded in `config.py`
- Files: `packages/backend/app/core/config.py` (lines 22, 41-42)
- Impact: Security risk if someone deploys without proper env vars
- Fix approach: Make these required env vars, fail fast if not set in production

**Incomplete API Router:**
- Issue: `tools_router` is imported and registered but no `tools.py` file exists in routers
- Files: `packages/backend/app/main.py` (line 74), `packages/backend/app/api/routers/`
- Impact: Potential missing functionality or dead code
- Fix approach: Verify if `tools.py` should exist or remove unused import

## Known Bugs

**No documented bugs found** - No TODO, FIXME, HACK, or XXX comments detected in codebase

## Security Considerations

**JWT Secret Key Weakness:**
- Risk: Default `APP_SECRET_KEY` is "insecure-dev-secret-key-change-me"
- Files: `packages/backend/app/core/config.py`
- Current mitigation: Checks if `app_debug=False` and raises RuntimeError if using default
- Recommendations: Ensure production deployments always set strong secret keys via env vars

**Hardcoded Default Credentials:**
- Risk: Default admin user credentials in config (`admin`/`password123`)
- Files: `packages/backend/app/core/config.py`
- Current mitigation: Only seeded if user doesn't exist
- Recommendations: Force users to set unique credentials via env vars before first deploy

**CORS Configuration:**
- Risk: `APP_CORS_ALLOWED_ORIGINS` defaults to `localhost:3000` only
- Files: `packages/backend/app/core/config.py`
- Current mitigation: Configurable via env var
- Recommendations: Ensure production CORS is properly restricted

**No Rate Limiting:**
- Risk: API endpoints may be vulnerable to abuse
- Files: All API routers
- Current mitigation: None detected
- Recommendations: Add rate limiting middleware (e.g., SlowAPI)

## Performance Bottlenecks

**DNSBL Sequential Checking:**
- Problem: DNSBL lookups may be done sequentially
- Files: `packages/backend/app/services/dnsbl.py`, `packages/backend/app/services/dnsbl_async.py`
- Cause: Async implementation exists but concurrency may be limited by `scan_concurrency` setting
- Improvement path: Ensure async DNS queries maximize concurrency

**Large Scan Result Sets:**
- Problem: No pagination in scan results retrieval
- Files: `packages/backend/app/db/client.py` (`get_results_by_job`, `get_results_by_block`)
- Cause: Default limits exist but no cursor-based pagination
- Improvement path: Add cursor-based pagination for large result sets

## Fragile Areas

**Supabase REST Dependency:**
- Why fragile: All DB ops depend on Supabase REST API; if API changes, client may break
- Files: `packages/backend/app/db/client.py`
- Safe modification: Test against Supabase API contract
- Test coverage: None (no tests exist)

**Celery Task State:**
- Why fragile: Tasks depend on Redis; if Redis fails mid-task, state is lost
- Files: `packages/backend/app/tasks/*.py`
- Safe modification: Ensure idempotent task design
- Test coverage: None

## Scaling Limits

**Redis Memory:**
- Current capacity: Docker volume with default Redis persistence
- Limit: Redis memory constrained by container limits
- Scaling path: Use Redis cluster or external managed Redis

**Supabase API Rate Limits:**
- Current capacity: Depends on Supabase plan
- Limit: REST API rate limits vary by plan
- Scaling path: Optimize queries, add caching layer

## Dependencies at Risk

**No obviously at-risk dependencies detected** - All dependencies are mainstream and actively maintained

## Missing Critical Features

**No Authentication Tests:**
- Problem: JWT auth exists but no tests verify token validation
- Blocks: Confidence in auth security

**No Webhook Signature Verification:**
- Problem: Webhooks sent to external URLs with no HMAC signature for verification
- Blocks: Webhook recipients can't verify authenticity

**No Rate Limiting:**
- Problem: No protection against API abuse
- Blocks: Production deployment without DDoS protection

## Test Coverage Gaps

**Backend API Layer:**
- What's not tested: All router endpoints
- Files: `packages/backend/app/api/routers/*.py`
- Risk: API behavior changes without detection
- Priority: High

**Backend Services Layer:**
- What's not tested: DNSBL checking, WHOIS lookup, AbuseIPDB integration
- Files: `packages/backend/app/services/*.py`
- Risk: External API integration failures go undetected
- Priority: High

**Frontend Components:**
- What's not tested: All React components
- Files: `packages/frontend/src/components/`, `packages/frontend/src/pages/`
- Risk: UI regressions undetected
- Priority: Medium

---

*Concerns audit: 2026-03-25*
