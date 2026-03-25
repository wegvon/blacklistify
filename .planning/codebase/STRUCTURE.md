# Codebase Structure

**Analysis Date:** 2026-03-25

## Directory Layout

```
blacklistify/                    # Project root
├── .github/workflows/            # GitHub Actions CI/CD
├── .gitignore                   # Git ignore rules
├── docker-compose.yml           # Production orchestration
├── docker-compose.dev.yml       # Dev orchestration
├── Dockerfile                   # Multi-stage build
├── LICENSE                      # MIT License
├── README.md                    # Project documentation
├── dev-plan.md                  # Development plan
├── supabase_setup.sql           # Database schema reference
├── supervisord.conf             # Process supervisor config
├── packages/
│   ├── backend/                 # Python/FastAPI backend
│   │   ├── app/
│   │   │   ├── api/routers/    # API route handlers
│   │   │   ├── core/            # Config, security, celery
│   │   │   ├── db/              # Supabase client wrapper
│   │   │   ├── models/          # SQLAlchemy models (unused?)
│   │   │   ├── schemas/          # Pydantic request/response models
│   │   │   ├── services/        # Business logic, external APIs
│   │   │   ├── tasks/           # Celery async tasks
│   │   │   └── main.py          # FastAPI app factory
│   │   ├── pyproject.toml       # Poetry dependencies
│   │   ├── requirements.txt     # pip dependencies (auto-generated?)
│   │   └── Dockerfile           # Multi-stage (backend, worker)
│   └── frontend/                 # React/Vite frontend
│       ├── src/
│       │   ├── components/       # Reusable UI components
│       │   ├── layouts/         # Page layout wrappers
│       │   ├── pages/           # Route page components
│       │   ├── routes/          # React Router config
│       │   ├── services/        # API client modules
│       │   ├── assets/          # Static assets
│       │   ├── App.jsx          # Root component
│       │   └── main.jsx         # Entry point
│       ├── public/              # Static public assets
│       ├── package.json         # Yarn dependencies
│       ├── vite.config.js       # Vite build config
│       ├── tailwind.config.js   # Tailwind CSS config
│       └── .eslintrc.cjs         # ESLint config
└── .env.example                 # Environment template
```

## Directory Purposes

**`packages/backend/app/api/routers/`:**
- Purpose: HTTP endpoint handlers
- Contains: `auth.py`, `blacklist.py`, `hostname.py`, `tools.py`, `api_keys.py`, `webhooks.py`, `subnets.py`, `scans.py`, `dashboard_api.py`
- Key files: Each router file handles a domain

**`packages/backend/app/core/`:**
- Purpose: Application-wide utilities
- Contains: `config.py` (settings), `security.py` (JWT, passwords), `celery_app.py` (Celery configuration)

**`packages/backend/app/db/`:**
- Purpose: Database access abstraction
- Contains: `client.py` (SupabaseDB wrapper class)
- Key files: `client.py`

**`packages/backend/app/services/`:**
- Purpose: Business logic and external integrations
- Contains: `dnsbl.py`, `dnsbl_async.py`, `whois_lookup.py`, `abuseipdb.py`, `server_status.py`, `cache.py`, `subnet_expander.py`

**`packages/backend/app/tasks/`:**
- Purpose: Async background jobs
- Contains: `scan_cycle.py`, `scan_subnet.py`, `notifications.py`, `cleanup.py`

**`packages/backend/app/schemas/`:**
- Purpose: Pydantic models for request/response validation
- Contains: `auth.py`, `subnet.py`, `webhook.py`, `api_key.py`, `scan.py`, `blacklist.py`, `hostname.py`

**`packages/frontend/src/components/`:**
- Purpose: Reusable React components
- Contains: `dashboard/`, `landing/`, `blacklist/` subdirectories with component files

**`packages/frontend/src/pages/`:**
- Purpose: Route-level page components
- Contains: `Landing.jsx`, `Login.jsx`, `dashboard/`, `blacklist/`, `subnets/`, `settings/`, `scans/`, `hostname/`, `tools/`

**`packages/frontend/src/services/`:**
- Purpose: API client modules
- Contains: `auth/`, `blacklist/`, `scans/`, `settings/`, `tools/`, `hostname/`, `subnets/`

## Key File Locations

**Entry Points:**
- `packages/backend/app/main.py`: FastAPI app factory (`create_app()`)
- `packages/frontend/src/main.jsx`: React entry point
- `packages/frontend/src/App.jsx`: Root React component

**Configuration:**
- `packages/backend/app/core/config.py`: Python settings (Settings dataclass)
- `packages/backend/pyproject.toml`: Poetry dependencies
- `packages/frontend/package.json`: Yarn dependencies
- `docker-compose.yml`: Container orchestration

**Core Logic:**
- `packages/backend/app/db/client.py`: Database operations (SupabaseDB class)
- `packages/backend/app/services/dnsbl_async.py`: DNSBL scanning logic
- `packages/backend/app/tasks/scan_cycle.py`: Periodic scan orchestration

**Testing:**
- No test directory detected (no `*test*.py`, `*spec*.py`, or `tests/` folder)

## Naming Conventions

**Files:**
- Python: snake_case (`dnsbl_async.py`, `scan_cycle.py`)
- React/JSX: PascalCase for components (`Navbar.jsx`, `Hero.jsx`), camelCase for non-components
- Config: dot notation (`.eslintrc.cjs`, `vite.config.js`)

**Directories:**
- Python: snake_case (`app/api/routers/`, `app/services/`)
- Frontend: kebab-case for paths (`blacklist-monitor/`, `subnet-detail/`)

**Functions/Methods:**
- Python: snake_case (`get_user_by_username`, `create_scan_job`)
- React: camelCase (`useAuth`, `handleSubmit`)

**Variables:**
- Python: snake_case (`scan_job`, `hashed_password`)
- JavaScript: camelCase (`scanJob`, `hashedPassword`)

**Types/Classes:**
- Python: PascalCase (`SupabaseDB`, `Settings`)
- JavaScript: PascalCase (React components), sometimes camelCase (hooks)

## Where to Add New Code

**New API Endpoint:**
- Implementation: `packages/backend/app/api/routers/<domain>.py`
- Schema: `packages/backend/app/schemas/<domain>.py`
- Service logic (if needed): `packages/backend/app/services/<domain>.py`
- Register router in `packages/backend/app/main.py`

**New Background Task:**
- Implementation: `packages/backend/app/tasks/<task_name>.py`
- Register task in `packages/backend/app/core/celery_app.py`
- Trigger via Celery beat schedule or API call

**New Frontend Page:**
- Implementation: `packages/frontend/src/pages/<domain>/<PageName>.jsx`
- Service (if needed): `packages/frontend/src/services/<domain>/index.jsx`
- Add route in `packages/frontend/src/routes/index.jsx`

**New Reusable Component:**
- Implementation: `packages/frontend/src/components/<category>/<ComponentName>.jsx`
- Follow existing patterns (headless UI, Mantine, Tailwind)

## Special Directories

**`packages/backend/app/models/`:**
- Purpose: SQLAlchemy model definitions
- Generated: No (manual)
- Committed: Yes
- Note: Models exist but Supabase REST API is used instead of SQLAlchemy ORM

**`packages/frontend/public/`:**
- Purpose: Static assets served as-is
- Generated: No
- Committed: Yes

**`.github/workflows/`:**
- Purpose: CI/CD pipeline definitions
- Generated: No
- Committed: Yes

**`packages/backend/app/schemas/`:**
- Purpose: Pydantic models for validation
- Generated: No (manual)
- Committed: Yes

---

*Structure analysis: 2026-03-25*
