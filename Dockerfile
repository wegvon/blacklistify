# =============================================================================
# Blacklistify — Multi-stage Dockerfile
# Targets: backend, worker, frontend
# =============================================================================

# ---------------------------------------------------------------------------
# Stage: backend-base (shared between API server and Celery worker)
# ---------------------------------------------------------------------------
FROM python:3.11-alpine AS backend-base

WORKDIR /app

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    libpq-dev \
    curl

COPY packages/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/backend/ ./

# ---------------------------------------------------------------------------
# Target: backend (FastAPI API server)
# ---------------------------------------------------------------------------
FROM backend-base AS backend

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]

# ---------------------------------------------------------------------------
# Target: worker (Celery worker + beat)
# ---------------------------------------------------------------------------
FROM backend-base AS worker

# No EXPOSE needed — worker doesn't serve HTTP
# Default CMD is overridden by docker-compose for worker vs beat
CMD ["celery", "-A", "app.core.celery_app", "worker", "-l", "info", "-c", "4", "-Q", "default,scans"]

# ---------------------------------------------------------------------------
# Stage: frontend-build (compile React app)
# ---------------------------------------------------------------------------
FROM node:18-alpine AS frontend-build

WORKDIR /app
COPY packages/frontend/package.json packages/frontend/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY packages/frontend/ ./
RUN yarn build

# ---------------------------------------------------------------------------
# Target: frontend (nginx serving static files + API proxy)
# ---------------------------------------------------------------------------
FROM nginx:alpine AS frontend

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY packages/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
