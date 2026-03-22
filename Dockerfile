# =============================================================================
# Blacklistify — Single Container (backend + frontend + worker)
# Coolify: tek Dockerfile deploy
# =============================================================================

# --- Stage 1: Build frontend ---
FROM node:18-alpine AS frontend-build

WORKDIR /app
COPY packages/frontend/package.json packages/frontend/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY packages/frontend/ ./
RUN yarn build

# --- Stage 2: Final image ---
FROM python:3.11-alpine

WORKDIR /app

# System deps
RUN apk add --no-cache \
    nginx \
    supervisor \
    curl \
    build-base \
    libffi-dev \
    libpq-dev \
    redis

# Python deps
COPY packages/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY packages/backend/ ./

# Frontend static files -> nginx
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Nginx config — Alpine nginx uses /etc/nginx/http.d/
RUN rm -f /etc/nginx/http.d/default.conf
COPY packages/frontend/nginx.conf /etc/nginx/http.d/default.conf

# Supervisord config
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
