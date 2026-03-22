# Ripefy Integration Guide

## Overview

Blacklistify reads subnet data from Ripefy's Supabase database (read-only) and stores scan results in a separate `blacklistify` schema.

## Setup

### 1. Create Database Role

```sql
CREATE ROLE blacklistify_app LOGIN PASSWORD 'secure-password';

-- Blacklistify schema: full access
GRANT ALL ON SCHEMA blacklistify TO blacklistify_app;
GRANT ALL ON ALL TABLES IN SCHEMA blacklistify TO blacklistify_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA blacklistify TO blacklistify_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA blacklistify GRANT ALL ON TABLES TO blacklistify_app;

-- Ripefy public schema: read only
GRANT USAGE ON SCHEMA public TO blacklistify_app;
GRANT SELECT ON public.subnets TO blacklistify_app;
GRANT SELECT ON public.leases TO blacklistify_app;
GRANT SELECT ON public.profiles TO blacklistify_app;
```

### 2. Run Migrations

```bash
cd packages/backend
DATABASE_URL=postgresql://blacklistify_app:password@db.xxx.supabase.co:6543/postgres \
  alembic upgrade head
```

### 3. Create API Key for Ripefy

1. Login to Blacklistify dashboard
2. Go to Settings > API Keys
3. Create key with scopes: `read`, `scan`
4. Copy the key (shown once)

### 4. Configure Webhook

1. Go to Settings > Webhooks
2. Add Ripefy webhook URL
3. Select events: `blacklist.detected`, `scan.completed`
4. Test the webhook

## API Usage from Ripefy

```python
import httpx

API_URL = "https://blacklistify.subnetpanel.com"
API_KEY = "blf_k1_..."

headers = {"X-API-Key": API_KEY}

# Get subnet summary
resp = httpx.get(f"{API_URL}/api/api/v1/subnets/summary", headers=headers)
summary = resp.json()

# Get specific subnet status
resp = httpx.get(f"{API_URL}/api/api/v1/subnets/{subnet_id}/status", headers=headers)
status = resp.json()

# Trigger manual scan
resp = httpx.post(f"{API_URL}/api/api/v1/subnets/{subnet_id}/scan", headers=headers)
```

## Data Flow

```
Ripefy Supabase (public.subnets)
    ↓ READ ONLY
Blacklistify Backend
    ↓ Celery Worker
DNSBL Providers (47+)
    ↓ Results
blacklistify.scan_results
    ↓ Aggregate
blacklistify.subnet_status
    ↓ Webhook
Ripefy (notification)
```

## Scan Schedule

| Scan Type | Frequency | Coverage |
|-----------|-----------|----------|
| Sampling | Every 6 hours | Representative IPs per /24 block |
| Full | Weekly (Sunday 02:00 UTC) | All IPs in all subnets |
| Manual | On demand | Single subnet or full cycle |
