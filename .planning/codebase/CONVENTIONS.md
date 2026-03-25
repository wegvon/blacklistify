# Coding Conventions

**Analysis Date:** 2026-03-25

## Naming Patterns

**Files:**
- Python: snake_case (`dnsbl_async.py`, `scan_cycle.py`, `api_keys.py`)
- React/JSX: PascalCase for components (`Navbar.jsx`, `Hero.jsx`, `StatGrid.jsx`)
- Config files: kebab or dot notation (`.eslintrc.cjs`, `vite.config.js`)

**Functions:**
- Python: snake_case (`get_user_by_username`, `create_scan_job`, `hash_password`)
- JavaScript: camelCase (`useAuth`, `handleSubmit`, `onClick`)

**Variables:**
- Python: snake_case (`scan_job`, `hashed_password`, `is_active`)
- JavaScript: camelCase (`scanJob`, `hashedPassword`, `isActive`)

**Types/Classes:**
- Python: PascalCase (`SupabaseDB`, `Settings`, `CeleryApp`)
- React Components: PascalCase (`DashboardLayout`, `BlacklistMonitor`)
- React Hooks: camelCase with `use` prefix (`useAuth`, `useFetch`)

**Constants:**
- Python: SCREAMING_SNAKE_CASE not consistently used (e.g., `default_admin_username`)
- JavaScript: camelCase or UPPER_SNAKE for true constants

## Code Style

**Formatting:**
- Python: Not formally configured (no black, yapf, ruff found)
- JavaScript: ESLint with `eslint:recommended`, `react/recommended`, `react-hooks/recommended`
- Key settings:
  - ES2020 environment
  - React 18.2 version specified
  - `react-refresh/only-export-components` as warn rule

**Linting:**
- Python: Not formally configured (no flake8, pylint, ruff configs found)
- JavaScript: ESLint with React plugin
- Key rules: React refresh safety, no unused vars, recommended patterns

**Tailwind CSS:**
- Configuration: `tailwind.config.js` with JIT mode
- Pattern: Utility classes in JSX, no custom CSS unless necessary

## Import Organization

**Python (FastAPI):**
```python
# Standard library
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# Third-party
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local (absolute imports from app root)
from app.api.routers import auth_router
from app.core.config import settings
```

**JavaScript (React):**
```javascript
// React ecosystem
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Third-party UI
import { Menu } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';

// Local components
import Navbar from './components/landing/Navbar';
import Hero from './components/landing/Hero';
```

**Path Aliases:**
- Frontend: No path aliases configured (relative imports used)
- Backend: No path aliases (absolute imports from `app` package)

## Error Handling

**Python (FastAPI):**
- HTTPExceptions for request errors: `raise HTTPException(status_code=404, detail="Not found")`
- Try/except for external APIs: `try: ... except Exception as e: logger.error(...)`
- Logging via module logger: `logger = logging.getLogger(__name__)`

**JavaScript (React):**
- Error boundaries: Not formally implemented
- Async errors: Try/catch with toast notifications
- API errors: Axios interceptors or inline error handling

## Logging

**Framework:** Python standard library `logging`

**Pattern:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Admin user already exists: %s", settings.default_admin_username)
logger.error("Failed to seed admin user: %s", e)
```

**No structured JSON logging detected**

## Comments

**When to Comment:**
- docstrings on modules and public functions (observed in `db/client.py`)
- inline comments for non-obvious logic
- No enforced comment policy

**JSDoc/TSDoc:**
- Not formally used in JavaScript code
- Python docstrings present in key files

## Function Design

**Size:** No strict limits observed; functions tend to be small and focused

**Parameters:**
- Python: Type hints not consistently used
- JavaScript: PropTypes not used (TypeScript not used)

**Return Values:**
- Python: Explicit returns, `dict | None` for optional returns
- JavaScript: Consistent return patterns in hooks

## Module Design

**Python Exports:**
- Explicit imports: `from app.api.routers import auth_router`
- No `__all__` exports observed

**Barrel Files:**
- Python: `__init__.py` files for package imports
- JavaScript: `index.jsx` files for service modules (`services/auth/index.jsx`)

---

*Convention analysis: 2026-03-25*
