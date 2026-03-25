# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.11+ - Backend API, tasks, services
- JavaScript (ES2020) - Frontend

**Secondary:**
- None detected

## Runtime

**Environment:**
- Python 3.11 via Poetry dependency management
- Node.js 18+ for frontend build

**Package Manager:**
- Poetry (Python) - Version 1.x via pyproject.toml
- Yarn (Frontend) - v1.x with .yarnrc configuration
- Lockfile: `yarn.lock` present, `poetry.lock` not committed

## Frameworks

**Core:**
- FastAPI 0.115.6 - Python web framework (REST API)
- Uvicorn 0.32.1 - ASGI server with standard extras

**Frontend:**
- React 18.2.0 - UI framework
- Vite 6.4.1 - Build tool and dev server
- React Router DOM 6.30.3 - Client-side routing

**UI Components:**
- Mantine 7.4.2 - React components library (core, hooks, notifications)
- Headless UI 1.7.18 - Unstyled, accessible components
- Heroicons v1 - Icon library
- React Icons 5.0.1 - Additional icons
- Tailwind CSS 3.4.1 - Utility-first CSS
- PostCSS 8.4.33 + Autoprefixer 10.4.17 - CSS processing

**Data Fetching:**
- Axios 1.13.6 - HTTP client (frontend)

## Key Dependencies

**Backend Core:**
- SQLAlchemy 2.0.36 - ORM (abstraction layer, currently unused with Supabase REST)
- Pydantic 2.10.3 - Data validation and settings management
- Passlib 1.7.4 - Password hashing
- python-jose 3.4.0 (with cryptography) - JWT token handling

**Database:**
- Supabase 2.11.0 - Backend-as-a-Service (REST API client for PostgreSQL)

**Task Queue:**
- Celery 5.4.0 - Async task queue
- Redis 5.2.0 - Message broker and result backend

**Async Operations:**
- aiodns 3.2.0 - Async DNS lookups (DNSBL scanning)
- httpx 0.28.0 - Async HTTP client (webhook delivery)
- requests 2.32.3 - Sync HTTP (fallback)

**Frontend Utilities:**
- classnames 2.5.1 - Conditional CSS classes
- jwt-decode 4.0.0 - JWT parsing (client-side)
- react-hot-toast 2.4.1 - Toast notifications
- react-typed 1.2.0 - Typed text animations
- react-toastify 10.0.4 - Alternative notifications

## Configuration

**Environment:**
- Environment variables via `python-dotenv` patterns
- Settings class in `packages/backend/app/core/config.py`
- `.env.example` files in backend and frontend packages

**Build:**
- Root: docker-compose.yml (multi-container orchestration)
- Backend: Dockerfile (multi-stage: backend, worker)
- Frontend: Dockerfile (multi-stage: frontend)
- Vite config: `packages/frontend/vite.config.js`
- Tailwind config: `packages/frontend/tailwind.config.js`
- ESLint: `packages/frontend/.eslintrc.cjs`
- Poetry: `packages/backend/pyproject.toml`

## Platform Requirements

**Development:**
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Redis (via Docker or local)

**Production:**
- Docker containerization
- Supabase PostgreSQL database (external)
- Redis for task queue (containerized)

---

*Stack analysis: 2026-03-25*
