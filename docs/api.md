# Blacklistify API Documentation

## Authentication

All `/api/v1/` endpoints require authentication via **JWT Bearer token** or **API Key**.

### JWT Token
```http
Authorization: Bearer <access_token>
```

### API Key
```http
X-API-Key: blf_k1_<random>
```

## Endpoints

### Legacy (backward compatible)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/user/create/` | No | Register user |
| POST | `/user/login/` | No | Login (returns tokens) |
| POST | `/user/token/refresh/` | No | Refresh access token |
| GET | `/blacklist/quick-check/?hostname=X` | No | DNSBL quick check |
| POST | `/blacklist/delist/` | JWT | Delist request |
| POST | `/hostname/` | JWT | Create hostname monitor |
| GET | `/hostname/list/` | JWT | List monitors |
| GET/PUT/DELETE | `/hostname/{pk}` | JWT | Monitor CRUD |
| GET | `/tools/abuseipdb/?hostname=X` | No | AbuseIPDB lookup |
| GET | `/tools/whois/?hostname=X` | No | WHOIS lookup |
| GET | `/tools/server-status/?hostname=X` | No | Server status check |

### Subnets (v1)
| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/api/v1/subnets/` | read | List active subnets (from Ripefy) |
| GET | `/api/v1/subnets/summary` | read | Aggregate blacklist summary |
| GET | `/api/v1/subnets/{id}` | read | Subnet details |
| GET | `/api/v1/subnets/{id}/status` | read | Subnet blacklist status |
| GET | `/api/v1/subnets/{id}/results` | read | Scan results for subnet |
| POST | `/api/v1/subnets/{id}/scan` | scan | Trigger manual subnet scan |

### Scans (v1)
| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/scans/` | scan | Trigger scan cycle |
| GET | `/api/v1/scans/` | read | List scan jobs |
| GET | `/api/v1/scans/{id}` | read | Scan job details |
| GET | `/api/v1/scans/{id}/results` | read | Scan job results |

### Dashboard (v1)
| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/api/v1/dashboard/` | read | Overall statistics |
| GET | `/api/v1/dashboard/worst-subnets` | read | Most blacklisted subnets |
| GET | `/api/v1/dashboard/timeline` | read | Blacklist trend over time |

### API Keys
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api-keys/` | JWT | Create API key |
| GET | `/api-keys/` | JWT | List API keys |
| DELETE | `/api-keys/{id}` | JWT | Revoke API key |

### Webhooks
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhooks/` | JWT | Create webhook |
| GET | `/webhooks/` | JWT | List webhooks |
| DELETE | `/webhooks/{id}` | JWT | Delete webhook |
| POST | `/webhooks/{id}/test` | JWT | Test webhook delivery |
| POST | `/webhooks/alerts/` | JWT | Create alert rule |
| GET | `/webhooks/alerts/` | JWT | List alert rules |
| DELETE | `/webhooks/alerts/{id}` | JWT | Delete alert rule |

## Webhook Events

| Event | Trigger |
|-------|---------|
| `blacklist.detected` | New blacklisted IP found |
| `blacklist.resolved` | Previously blacklisted IP cleared |
| `scan.completed` | Scan cycle completed |
| `scan.failed` | Scan cycle failed |
| `alert.threshold` | Blacklist rate threshold exceeded |

### Webhook Payload
```json
{
  "event": "blacklist.detected",
  "timestamp": "2026-03-23T14:00:00Z",
  "data": {
    "subnet_id": "uuid",
    "subnet_cidr": "109.236.48.0/22",
    "blacklisted_count": 3,
    "scan_job_id": 1234,
    "alert_rule": "High blacklist rate"
  },
  "signature": "sha256=abc123..."
}
```

Verify webhook signatures using HMAC-SHA256 with the secret provided during webhook creation.
