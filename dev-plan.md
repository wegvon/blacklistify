# Blacklistify — Development Plan

> **Tarih:** 2026-03-23
> **Proje:** bekkaze/abusebox fork → subnetpanel/blacklistify
> **Amac:** 70.000+ IP'nin surekli DNSBL blacklist monitoring'i
> **Yaklasim:** Monorepo, Ripefy Supabase (ortak DB), Celery scheduler, CIDR-native

---

## 1. Mimari Karar: Ortak Supabase DB

### Neden Ayri DB Degil?

Ripefy'in Supabase'inde subnet verileri zaten mevcut. Ayri bir PostgreSQL ayaga kaldirmak:
- Veri duplikasyonu yaratir (subnet'ler iki yerde)
- Sync mekanizmasi gerektirir (Ripefy ↔ Blacklistify)
- Operasyonel karmasiklik ekler

Bunun yerine Blacklistify, Ripefy'in Supabase DB'sine **ayri bir schema** uzerinden baglanir:

```
Supabase PostgreSQL
├── public schema          # Ripefy tablolari (subnets, leases, users, ...)
└── blacklistify schema    # Blacklistify tablolari (scan_results, scan_jobs, ...)
```

### Avantajlar

- Subnet verisi tek kaynaktan (single source of truth)
- Import/sync mekanizmasina gerek yok
- Ripefy'da yeni subnet eklenince Blacklistify otomatik gorur
- JOIN ile zengin sorgular (subnet + scan result + lease bilgisi)
- Altyapi maliyeti sifir (ekstra DB yok)

### Riskler ve Onlemler

| Risk | Onlem |
|------|-------|
| Blacklistify Ripefy verilerini bozar | `blacklistify` schema'si izole, public'e sadece READ erisimiSupabase service_role key yerine ozel bir DB role olustur |
| DB performans etkisi | Scan result'lar ayri schema'da, Ripefy sorgularini etkilemez. Index'ler dogru konursa sorun olmaz |
| Supabase connection limit | Supabase Pro plan: 60 direct / 200 pooler connection. Blacklistify pooler kullanmali |

### DB Erisim Matrisi

| Tablo | Blacklistify Erisimi |
|-------|---------------------|
| `public.subnets` (Ripefy) | **READ ONLY** — subnet listesi ve CIDR bilgisi |
| `public.leases` (Ripefy) | **READ ONLY** — aktif lease durumu |
| `public.profiles` (Ripefy) | **READ ONLY** — musteri bilgisi (alert gondermek icin) |
| `blacklistify.*` | **READ/WRITE** — tum scan tablolari |

---

## 2. Mevcut AbuseBox Durum Analizi

### 2.1 Kod Yapisi

```
bekkaze/abusebox (mevcut)
├── backend/          # FastAPI 0.115.6, SQLAlchemy 2.0, SQLite
│   ├── app/
│   │   ├── main.py              # App factory, lifespan (DB init + admin seed)
│   │   ├── core/config.py       # Pydantic settings (env vars)
│   │   ├── core/security.py     # JWT HS256 + PBKDF2-SHA256
│   │   ├── models/              # 4 model: User, Hostname, CheckHistory, BlacklistedHostname
│   │   ├── schemas/             # Pydantic v2 request/response
│   │   ├── api/routers/         # 4 router: auth, hostname, blacklist, tools
│   │   ├── services/            # dnsbl (41 provider, 12 thread), abuseipdb, whois, server_status
│   │   └── db/                  # SQLAlchemy session + init_data seed
│   ├── requirements.txt         # 7 paket
│   └── Dockerfile               # python:3.11-alpine, uvicorn :8100
│
├── frontend/         # React 18.2, Vite, Mantine UI, Tailwind CSS
│   ├── src/
│   │   ├── pages/               # Landing, Login, blacklist/, dashboard/
│   │   ├── components/          # blacklist/, dashboard/, landing/
│   │   ├── services/            # API client (axios)
│   │   └── routes/              # React Router
│   ├── package.json             # yarn, node:18-alpine
│   └── Dockerfile               # yarn dev :3000 (DEV SERVER!)
│
└── docker-compose.yml           # 2 servis, no volumes
```

### 2.2 Kritik Eksikler

| # | Eksik | Etki | Oncelik |
|---|-------|------|---------|
| 1 | SQLite | Concurrent write lock, olceklenmez | P0 — Supabase ile cozulecek |
| 2 | Scheduler yok | Periyodik tarama mumkun degil | P0 |
| 3 | Bulk/CIDR desteği yok | Subnet eklenemez | P0 — Supabase'den okuyarak cozulecek |
| 4 | Frontend dev server | Production'da `yarn dev` calisiyor | P0 |
| 5 | Rate limiting yok | DNSBL provider ban riski | P1 |
| 6 | API key auth yok | Dis entegrasyon icin JWT yetersiz | P1 |
| 7 | Webhook/callback yok | Blacklist degisikliginde bildirim yok | P1 |
| 8 | Test yok | Regression riski | P1 |
| 9 | Async DNS yok | ThreadPool(12) ile 70K IP icin ~8 saat | P2 |
| 10 | Caching yok | Gereksiz tekrar sorgu | P2 |

### 2.3 DNSBL Engine Performans Hesabi

```
Mevcut:
  41 provider × 1 IP = 41 DNS sorgusu
  12 thread, 1.5sn timeout = ~5sn/IP
  70.000 IP × 5sn = ~97 saat (tek thread)
  12 thread ile = ~8 saat/full cycle

Hedef (async + sampling):
  aiodns resolver, 100 concurrent
  Sampling: her /24'ten 1 representative IP
  ~280 subnet × 1 sample = 280 IP × 41 provider = 11.480 sorgu
  100 concurrent, 2sn avg = ~4 dakika (sampling cycle)
  Full scan (haftalik): ~2.5 saat
```

---

## 3. Hedef Mimari

### 3.1 Monorepo Yapisi

```
blacklistify/
├── README.md
├── docker-compose.yml           # redis, backend, worker, beat, frontend
├── docker-compose.dev.yml       # Dev overrides
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml               # Lint + test
│       └── deploy.yml           # Coolify webhook trigger
│
├── packages/
│   ├── backend/                 # FastAPI API + Celery worker
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   │   ├── config.py          # GUNCELLE: Supabase connection
│   │   │   │   ├── security.py
│   │   │   │   └── celery_app.py      # YENİ: Celery config
│   │   │   ├── models/
│   │   │   │   ├── user.py            # KORUNACAK: Blacklistify local users
│   │   │   │   ├── hostname.py        # KORUNACAK: Legacy tek IP kayitlari
│   │   │   │   ├── check_history.py   # KORUNACAK: Legacy
│   │   │   │   ├── scan_job.py        # YENİ: Scan job tracking
│   │   │   │   ├── scan_result.py     # YENİ: IP bazli scan sonuclari
│   │   │   │   ├── alert_rule.py      # YENİ: Alert konfigurasyonu
│   │   │   │   └── api_key.py         # YENİ: API key model
│   │   │   ├── schemas/
│   │   │   │   ├── subnet.py          # YENİ: Supabase subnet read schema
│   │   │   │   ├── scan.py            # YENİ: Scan request/response
│   │   │   │   └── api_key.py         # YENİ
│   │   │   ├── api/routers/
│   │   │   │   ├── auth.py
│   │   │   │   ├── subnets.py         # YENİ: Supabase subnet okuma + scan tetikleme
│   │   │   │   ├── scans.py           # YENİ: Scan sonuclari + gecmis
│   │   │   │   ├── blacklist.py       # KORUNACAK: quick-check (tek IP)
│   │   │   │   ├── tools.py           # KORUNACAK: whois, abuseipdb, server-status
│   │   │   │   ├── api_keys.py        # YENİ
│   │   │   │   └── webhooks.py        # YENİ
│   │   │   ├── services/
│   │   │   │   ├── dnsbl.py           # KORUNACAK: sync engine (fallback)
│   │   │   │   ├── dnsbl_async.py     # YENİ: aiodns-based resolver
│   │   │   │   ├── subnet_reader.py   # YENİ: Supabase'den subnet oku
│   │   │   │   ├── subnet_expander.py # YENİ: CIDR → IP listesi
│   │   │   │   ├── cache.py           # YENİ: Redis cache layer
│   │   │   │   ├── abuseipdb.py
│   │   │   │   ├── whois_lookup.py
│   │   │   │   └── server_status.py
│   │   │   ├── tasks/                 # YENİ: Celery tasks
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scan_cycle.py      # Periyodik full/sampling cycle
│   │   │   │   ├── scan_subnet.py     # Tek subnet tarama
│   │   │   │   ├── notifications.py   # Webhook/alert gonderimi
│   │   │   │   └── cleanup.py         # Eski sonuclari temizle
│   │   │   └── db/
│   │   │       ├── session.py         # GUNCELLE: Supabase PostgreSQL
│   │   │       ├── supabase_read.py   # YENİ: Read-only Supabase client
│   │   │       └── migrations/        # YENİ: Alembic (sadece blacklistify schema)
│   │   ├── tests/
│   │   │   ├── test_dnsbl.py
│   │   │   ├── test_subnet_reader.py
│   │   │   └── test_api.py
│   │   ├── alembic.ini
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── Dockerfile.worker
│   │
│   └── frontend/
│       ├── src/
│       │   ├── pages/
│       │   │   ├── Login.jsx
│       │   │   ├── dashboard/         # GUNCELLE: scan summary ekle
│       │   │   ├── blacklist/         # KORUNACAK: tek IP check
│       │   │   └── subnets/           # YENİ: Subnet monitoring sayfasi
│       │   ├── components/
│       │   │   ├── dashboard/
│       │   │   ├── blacklist/
│       │   │   └── subnets/           # YENİ
│       │   ├── services/
│       │   └── routes/
│       ├── package.json
│       ├── nginx.conf                 # YENİ: Production serving
│       └── Dockerfile                 # GUNCELLE: multi-stage build
│
└── docs/
    ├── api.md
    └── ripefy-integration.md
```

### 3.2 Docker Compose (Hedef)

```yaml
# docker-compose.yml
# NOT: PostgreSQL yok — Ripefy'in Supabase'i kullaniliyor

services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      retries: 3

  backend:
    build: ./packages/backend
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: ${SUPABASE_DB_URL}
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      APP_SECRET_KEY: ${APP_SECRET_KEY}
    ports:
      - "8100:8100"

  worker:
    build:
      context: ./packages/backend
      dockerfile: Dockerfile.worker
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: ${SUPABASE_DB_URL}
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    command: celery -A app.core.celery_app worker -l info -c 4 -Q default,scans

  beat:
    build:
      context: ./packages/backend
      dockerfile: Dockerfile.worker
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_healthy
    environment:
      CELERY_BROKER_URL: redis://redis:6379/0
    command: celery -A app.core.celery_app beat -l info --schedule /tmp/celerybeat-schedule

  frontend:
    build: ./packages/frontend
    restart: unless-stopped
    ports:
      - "3000:80"

volumes:
  redisdata:
```

### 3.3 Veri Akisi

```
┌─────────────────────────────────────────────────────────────┐
│                    Supabase PostgreSQL                       │
│                                                             │
│  public schema (Ripefy)      blacklistify schema            │
│  ┌──────────────┐            ┌───────────────────┐          │
│  │ subnets      │──READ──────│ scan_jobs         │          │
│  │ leases       │            │ scan_results      │          │
│  │ profiles     │            │ alert_rules       │          │
│  └──────────────┘            │ api_keys          │          │
│                              │ users (local)     │          │
│                              │ webhooks          │          │
│                              └───────────────────┘          │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │ Backend │   │ Worker  │   │  Beat   │
   │ (API)   │   │ (Scan)  │   │ (Cron)  │
   └────┬────┘   └────┬────┘   └─────────┘
        │              │
        │         ┌────▼────┐
        │         │  Redis  │
        │         │ (Cache  │
        │         │ +Broker)│
        │         └─────────┘
        │
   ┌────▼────┐
   │Frontend │
   │ (React) │
   └─────────┘
```

---

## 4. Supabase Schema Tasarimi

### 4.1 Blacklistify Schema Tablolari

```sql
-- Schema olustur
CREATE SCHEMA IF NOT EXISTS blacklistify;

-- Scan job'lari (her tarama cycle'i bir job)
CREATE TABLE blacklistify.scan_jobs (
    id              BIGSERIAL PRIMARY KEY,
    job_type        VARCHAR(20) NOT NULL,       -- 'sampling', 'full', 'single', 'manual'
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    total_subnets   INT DEFAULT 0,
    total_ips       INT DEFAULT 0,
    scanned_ips     INT DEFAULT 0,
    blacklisted_ips INT DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- IP bazli scan sonuclari
CREATE TABLE blacklistify.scan_results (
    id                  BIGSERIAL PRIMARY KEY,
    scan_job_id         BIGINT REFERENCES blacklistify.scan_jobs(id) ON DELETE CASCADE,
    subnet_id           UUID,                       -- Ripefy public.subnets.id referansi (soft FK)
    subnet_cidr         VARCHAR(43) NOT NULL,       -- Denormalize: "109.236.48.0/22"
    ip_address          INET NOT NULL,              -- PostgreSQL native IP tipi
    is_blacklisted      BOOLEAN DEFAULT FALSE,
    providers_detected  JSONB DEFAULT '[]',         -- [{"provider":"spamhaus","categories":["spam"]}]
    providers_total     INT DEFAULT 0,
    checked_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Performans index'leri
CREATE INDEX idx_scan_results_subnet ON blacklistify.scan_results(subnet_cidr);
CREATE INDEX idx_scan_results_ip ON blacklistify.scan_results(ip_address);
CREATE INDEX idx_scan_results_blacklisted ON blacklistify.scan_results(is_blacklisted) WHERE is_blacklisted = TRUE;
CREATE INDEX idx_scan_results_checked ON blacklistify.scan_results(checked_at DESC);
CREATE INDEX idx_scan_results_job ON blacklistify.scan_results(scan_job_id);

-- Subnet bazli aggregate cache (materialized view yerine tablo, Celery gunceller)
CREATE TABLE blacklistify.subnet_status (
    subnet_id           UUID PRIMARY KEY,           -- Ripefy public.subnets.id
    subnet_cidr         VARCHAR(43) NOT NULL,
    total_ips           INT DEFAULT 0,
    blacklisted_ips     INT DEFAULT 0,
    clean_ips           INT DEFAULT 0,
    blacklist_rate      DECIMAL(5,4) DEFAULT 0,     -- 0.0312 = %3.12
    worst_providers     JSONB DEFAULT '[]',         -- ["spamhaus", "barracuda"]
    last_scan_job_id    BIGINT,
    last_scanned_at     TIMESTAMPTZ,
    status_changed_at   TIMESTAMPTZ,                -- Son blacklist degisikligi
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- API key'ler
CREATE TABLE blacklistify.api_keys (
    id          BIGSERIAL PRIMARY KEY,
    key_prefix  VARCHAR(8) NOT NULL,                -- "blf_k1_"
    key_hash    VARCHAR(128) NOT NULL,
    name        VARCHAR(100) NOT NULL,              -- "Ripefy Production"
    scopes      JSONB DEFAULT '["read"]',           -- ["read", "write", "scan"]
    is_active   BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_prefix ON blacklistify.api_keys(key_prefix);

-- Webhook'lar
CREATE TABLE blacklistify.webhooks (
    id          BIGSERIAL PRIMARY KEY,
    url         VARCHAR(500) NOT NULL,
    events      JSONB NOT NULL,                     -- ["blacklist.detected","scan.completed"]
    secret      VARCHAR(128) NOT NULL,              -- HMAC signing
    is_active   BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    failure_count INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Alert kurallari
CREATE TABLE blacklistify.alert_rules (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    condition_type  VARCHAR(30) NOT NULL,            -- 'blacklist_detected', 'blacklist_rate_above', 'scan_failed'
    threshold       DECIMAL,                         -- ornegin: 0.05 = %5 blacklist rate
    subnet_filter   VARCHAR(43),                     -- NULL = tum subnet'ler, veya spesifik CIDR
    webhook_id      BIGINT REFERENCES blacklistify.webhooks(id),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 Supabase DB Role (Guvenlik)

```sql
-- Blacklistify icin ozel DB role
CREATE ROLE blacklistify_app LOGIN PASSWORD 'secure-password';

-- Kendi schema'sina full erisim
GRANT ALL ON SCHEMA blacklistify TO blacklistify_app;
GRANT ALL ON ALL TABLES IN SCHEMA blacklistify TO blacklistify_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA blacklistify TO blacklistify_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA blacklistify GRANT ALL ON TABLES TO blacklistify_app;

-- Ripefy tablolarina sadece READ
GRANT USAGE ON SCHEMA public TO blacklistify_app;
GRANT SELECT ON public.subnets TO blacklistify_app;
GRANT SELECT ON public.leases TO blacklistify_app;
GRANT SELECT ON public.profiles TO blacklistify_app;

-- ONEMLI: public'e INSERT/UPDATE/DELETE yok
-- Blacklistify, Ripefy verilerini ASLA degistiremez
```

### 4.3 Ripefy Subnets Tablosu (Mevcut, Okuma)

Blacklistify bu tabloyu READ ONLY olarak kullanir. Ripefy'daki subnet tablosunun yapisina gore
`subnet_reader.py` servisi adapte edilecek. Beklenen minimum alanlar:

```
public.subnets (Ripefy — mevcut)
├── id (UUID)
├── cidr (VARCHAR)          -- "109.236.48.0/22"
├── description (TEXT)
├── status (VARCHAR)        -- active, reserved, etc.
├── customer_id (UUID)
└── created_at (TIMESTAMPTZ)
```

> **Not:** Sprint 1'de Ripefy'in gercek tablo yapisini inceleyip subnet_reader.py'i ona gore yazmak gerekecek.

---

## 5. Sprint Plani

### Sprint 0 — Fork + Monorepo Gecisi (1-2 gun)

**Amac:** Fork, monorepo yapisina cevir, temel altyapi.

- [ ] `bekkaze/abusebox` → `subnetpanel/blacklistify` olarak forkla
- [ ] Repo adi ve tum referanslari `blacklistify` olarak guncelle
- [ ] Dizin yapisini `packages/backend` ve `packages/frontend` olarak tasi
- [ ] Root `docker-compose.yml` olustur (redis, backend, worker, beat, frontend)
- [ ] `docker-compose.dev.yml` ile development overrides
- [ ] `.env.example` dosyasi (Supabase connection bilgileri dahil)
- [ ] `.github/workflows/ci.yml` — lint + test pipeline
- [ ] Root `README.md`

**Monorepo tasimasi:**
```
# Eski → Yeni
backend/              → packages/backend/
frontend/             → packages/frontend/
docker-compose.yml    → docker-compose.yml (yeniden yazilacak, postgres yok)
```

**Checklist:**
- [ ] `docker compose up` ile redis, backend, frontend ayaga kalkiyor mu?
- [ ] Health check endpoint calisiyor mu?

---

### Sprint 1 — Supabase Entegrasyonu (2-3 gun)

**Amac:** SQLite'i kaldir, Ripefy'in Supabase PostgreSQL'ine baglan, blacklistify schema'sini olustur.

#### 1.1 DB Baglantisi

- [ ] `requirements.txt`'e ekle: `asyncpg`, `psycopg2-binary`, `alembic`, `supabase`
- [ ] `db/session.py` — Supabase PostgreSQL connection (pooler mode)
- [ ] `db/supabase_read.py` — Supabase Python client (public tablolar icin read-only)
- [ ] `core/config.py` — `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- [ ] SQLite-spesifik kodlari temizle

#### 1.2 Schema + Migrations

- [ ] `alembic init` — blacklistify schema icin migration altyapisi
- [ ] Initial migration: Section 4.1'deki tum tablolari olustur
- [ ] DB role olustur (Section 4.2)

#### 1.3 Subnet Reader Service

```python
# packages/backend/app/services/subnet_reader.py

from supabase import create_client

class SubnetReader:
    """Ripefy'in Supabase'inden subnet verilerini okur (READ ONLY)."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.client = create_client(supabase_url, supabase_key)

    async def get_active_subnets(self) -> list[dict]:
        """Tum aktif subnet'leri getirir."""
        result = self.client.table("subnets") \
            .select("id, cidr, description, status, customer_id") \
            .eq("status", "active") \
            .execute()
        return result.data

    async def get_subnet_by_id(self, subnet_id: str) -> dict | None:
        """Tek subnet getirir."""
        result = self.client.table("subnets") \
            .select("*") \
            .eq("id", subnet_id) \
            .single() \
            .execute()
        return result.data

    async def get_subnets_by_customer(self, customer_id: str) -> list[dict]:
        """Musteriye ait subnet'leri getirir."""
        result = self.client.table("subnets") \
            .select("id, cidr, description") \
            .eq("customer_id", customer_id) \
            .eq("status", "active") \
            .execute()
        return result.data
```

> **Onemli:** Sprint basinda Ripefy'in gercek `subnets` tablo yapisini inceleyip bu servisi ona gore adapte et.

#### 1.4 Ripefy Tablo Yapisi Kesfetme

- [ ] Supabase dashboard'dan `public.subnets` tablo yapisini incele
- [ ] Subnet CIDR bilgisinin hangi kolonda oldugunu dogrula
- [ ] Aktif/pasif filtreleme icin kullanilacak status kolonunu belirle
- [ ] `subnet_reader.py`'i gercek yapiya gore guncelle

**Yeni dependency'ler:**
```
asyncpg==0.30.0
psycopg2-binary==2.9.10
alembic==1.14.0
supabase==2.11.0
```

**Checklist:**
- [ ] `alembic upgrade head` — blacklistify schema'si olusturuluyor mu?
- [ ] `SubnetReader.get_active_subnets()` Ripefy subnet'lerini donuyor mu?
- [ ] Mevcut AbuseBox endpoint'leri hala calisiyor mu? (backward compat)
- [ ] Supabase connection pooler uzerinden calisiyor mu?

---

### Sprint 2 — Celery Scheduler + Background Scanning (3-4 gun)

**Amac:** Periyodik subnet taramasi icin Celery + Redis altyapisi.

#### 2.1 Celery Konfigurasyonu

```python
# packages/backend/app/core/celery_app.py

from celery import Celery
from celery.schedules import crontab

celery = Celery("blacklistify")
celery.config_from_object({
    "broker_url": settings.CELERY_BROKER_URL,
    "result_backend": settings.CELERY_RESULT_BACKEND,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "task_routes": {
        "app.tasks.scan_*": {"queue": "scans"},
        "app.tasks.notifications.*": {"queue": "default"},
    },
    "beat_schedule": {
        "sampling-scan": {
            "task": "app.tasks.scan_cycle.run_sampling_scan",
            "schedule": crontab(minute=0, hour="*/6"),  # Her 6 saatte
        },
        "full-scan-weekly": {
            "task": "app.tasks.scan_cycle.run_full_scan",
            "schedule": crontab(minute=0, hour=2, day_of_week=0),  # Pazar 02:00
        },
        "cleanup-old-results": {
            "task": "app.tasks.cleanup.purge_old_results",
            "schedule": crontab(minute=0, hour=3),  # Her gece 03:00
        },
        "refresh-subnet-status": {
            "task": "app.tasks.scan_cycle.refresh_subnet_status",
            "schedule": crontab(minute="*/30"),  # Her 30 dakikada
        },
    },
})
```

#### 2.2 Scan Cycle Task

```python
# packages/backend/app/tasks/scan_cycle.py

@celery.task(bind=True)
def run_sampling_scan(self):
    """
    Sampling tarama: her subnet'ten representative IP'ler secer ve tarar.

    Strateji:
      /24 → tum 254 IP (kucuk, hizli)
      /22 → her /24 blogundan 1 IP = 4 sample
      /20 → her /24 blogundan 1 IP = 16 sample
      /16 → her /24 blogundan 1 IP = 256 sample

    Blacklist tespit edilirse → o /24 full scan'e alinir.
    """
    # 1. Supabase'den aktif subnet'leri al
    # 2. Her subnet icin sampling IP listesi olustur
    # 3. Batch'lere bol, her batch'i scan_subnet task'ina gonder
    # 4. Sonuclari scan_results'a yaz
    # 5. subnet_status tablosunu guncelle
    # 6. Degisiklik varsa alert tetikle
    pass

@celery.task(bind=True)
def run_full_scan(self):
    """Haftalik full scan: tum subnet'lerin tum IP'leri (cache'siz)."""
    pass

@celery.task
def refresh_subnet_status():
    """subnet_status tablosunu scan_results'dan yeniden hesapla."""
    pass
```

#### 2.3 Rate Limiting Config

```python
SCAN_CONFIG = {
    "batch_size": 50,              # Ayni anda max 50 IP scan'e gonder
    "batch_delay_seconds": 2,      # Batch'ler arasi bekleme
    "provider_timeout": 2.0,       # DNS sorgu timeout
    "max_concurrent_dns": 100,     # Async DNS concurrent limit
    "retry_on_timeout": False,     # Timeout'ta tekrar deneme
    "cache_ttl_hours": 6,          # Redis cache suresi
    "full_scan_cache_bypass": True, # Haftalik full scan cache atlar
}
```

- [ ] `celery_app.py` konfigurasyonu
- [ ] `tasks/scan_cycle.py` — sampling + full scan orchestration
- [ ] `tasks/scan_subnet.py` — tek subnet tarama task'i
- [ ] `tasks/notifications.py` — webhook/alert gonderimi
- [ ] `tasks/cleanup.py` — 30 gunluk scan sonuclarini temizle
- [ ] `Dockerfile.worker` — Celery worker container
- [ ] `services/cache.py` — Redis cache layer
- [ ] Beat schedule: 6 saatlik sampling + haftalik full + 30dk status refresh

**Yeni dependency'ler:**
```
celery==5.4.0
redis==5.2.0
```

**Checklist:**
- [ ] Worker basliyor, beat schedule tetikleniyor mu?
- [ ] Sampling scan Supabase'den subnet'leri aliyor mu?
- [ ] Scan sonuclari `blacklistify.scan_results`'a yaziliyor mu?
- [ ] `blacklistify.subnet_status` guncelleniyor mu?
- [ ] Redis cache calisiyor mu?

---

### Sprint 3 — Async DNSBL Engine (2-3 gun)

**Amac:** Sync ThreadPoolExecutor'u async DNS resolver ile degistir.

#### 3.1 Async Engine

```python
# packages/backend/app/services/dnsbl_async.py

import aiodns
import asyncio
from app.services.cache import RedisCache

class AsyncDNSBLChecker:
    def __init__(self, providers: list[str], concurrency: int = 100,
                 timeout: float = 2.0, cache: RedisCache = None):
        self.providers = providers
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.resolver = aiodns.DNSResolver(timeout=timeout)
        self.cache = cache

    async def check_ip(self, ip: str) -> dict:
        """Tek IP'yi tum provider'larda kontrol eder."""
        # Cache kontrol
        if self.cache:
            cached = await self.cache.get(f"dnsbl:{ip}")
            if cached:
                return cached

        reversed_ip = ".".join(reversed(ip.split(".")))
        tasks = [self._check_provider(reversed_ip, p) for p in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        detected = []
        checked = 0
        for r in results:
            if isinstance(r, Exception):
                continue
            provider, is_listed = r
            checked += 1
            if is_listed:
                detected.append({"provider": provider, "status": "open"})

        result = {
            "ip": ip,
            "is_blacklisted": len(detected) > 0,
            "providers_detected": detected,
            "providers_total": checked,
        }

        # Cache'e yaz
        if self.cache:
            await self.cache.set(f"dnsbl:{ip}", result, ttl_hours=6)

        return result

    async def check_batch(self, ips: list[str]) -> list[dict]:
        """Birden fazla IP'yi paralel kontrol eder."""
        tasks = [self.check_ip(ip) for ip in ips]
        return await asyncio.gather(*tasks)

    async def _check_provider(self, reversed_ip: str, provider: str) -> tuple[str, bool]:
        async with self.semaphore:
            try:
                await self.resolver.query(f"{reversed_ip}.{provider}", "A")
                return (provider, True)
            except aiodns.error.DNSError:
                return (provider, False)
```

#### 3.2 Performans Karsilastirmasi

```
Mevcut (sync, ThreadPool 12):
  1 IP    = ~5sn
  100 IP  = ~42sn
  70K IP  = ~8 saat

Hedef (async, 100 concurrent + cache):
  1 IP    = ~2sn
  100 IP  = ~4sn
  70K IP  = ~2.5 saat (full, cache'siz)
  70K IP  = ~45dk (sampling mode)
  70K IP  = ~20dk (sampling + cache hit %70)
```

- [ ] `dnsbl_async.py` — aiodns-based async checker
- [ ] Redis cache entegrasyonu
- [ ] `check_batch()` methodu
- [ ] Semaphore ile concurrency kontrolu
- [ ] Mevcut sync `dnsbl.py`'i fallback olarak tut
- [ ] Celery task'larini async engine'e bagla

**Yeni dependency:**
```
aiodns==3.2.0
```

**Checklist:**
- [ ] Async engine sync ile ayni sonuclari donuyor mu?
- [ ] 100 IP batch'i timeout olmadan tamamlaniyor mu?
- [ ] Cache hit/miss oranlari loglanıyor mu?

---

### Sprint 4 — API Key Auth + Webhook (2 gun)

**Amac:** Dis entegrasyonlar (Ripefy) icin API key ve webhook destegi.

#### 4.1 API Key Kullanimi

```http
# JWT yerine API key ile erisim
GET /api/v1/subnets/summary
X-API-Key: blf_k1_a3f8c9d2e1b0...
```

#### 4.2 Auth Middleware

```python
# Her endpoint'te: JWT OR API Key kabul et
async def get_current_auth(
    jwt_user: User | None = Depends(get_current_user_optional),
    api_key: str | None = Header(None, alias="X-API-Key"),
) -> AuthContext:
    if jwt_user:
        return AuthContext(type="jwt", user=jwt_user)
    if api_key:
        key_record = await validate_api_key(api_key)
        return AuthContext(type="api_key", key=key_record)
    raise AuthError("Authentication required")
```

#### 4.3 Webhook Events

| Event | Tetikleyici |
|-------|------------|
| `blacklist.detected` | Yeni blacklist tespit edildi |
| `blacklist.resolved` | Onceden blacklisted IP temizlendi |
| `scan.completed` | Scan cycle tamamlandi |
| `scan.failed` | Scan cycle hata ile sonuclandi |
| `alert.threshold` | Blacklist rate threshold asildi |

**Webhook Payload:**
```json
{
  "event": "blacklist.detected",
  "timestamp": "2026-03-23T14:00:00Z",
  "data": {
    "subnet_id": "uuid-here",
    "subnet_cidr": "109.236.48.0/22",
    "ip": "109.236.49.15",
    "provider": "spamhaus",
    "categories": ["spam"],
    "scan_job_id": 1234
  },
  "signature": "sha256=abc123..."
}
```

- [ ] API key CRUD endpoint'leri: `POST/GET/DELETE /api-keys/`
- [ ] Auth middleware: JWT OR API key
- [ ] Webhook CRUD endpoint'leri: `POST/GET/DELETE /webhooks/`
- [ ] Webhook delivery service (exponential backoff retry)
- [ ] HMAC-SHA256 signature ile webhook guvenlik
- [ ] Webhook test endpoint: `POST /webhooks/{id}/test`

---

### Sprint 5 — Scan API Endpoint'leri (2 gun)

**Amac:** Frontend ve Ripefy icin scan sonuclarina erisim API'si.

#### 5.1 Endpoint'ler

```
# Subnet'ler (Supabase'den okuma)
GET    /api/v1/subnets/                     # Tum aktif subnet'ler (Ripefy'dan)
GET    /api/v1/subnets/{id}/                # Subnet detay
GET    /api/v1/subnets/summary/             # Aggregate blacklist durumu

# Scan islemleri
POST   /api/v1/scans/                       # Manuel scan tetikle
GET    /api/v1/scans/                       # Scan job listesi
GET    /api/v1/scans/{job_id}/              # Scan job detay
GET    /api/v1/scans/{job_id}/results/      # Job'un sonuclari

# Subnet bazli sonuclar
GET    /api/v1/subnets/{id}/status/         # Subnet blacklist durumu
GET    /api/v1/subnets/{id}/results/        # Subnet scan gecmisi
GET    /api/v1/subnets/{id}/scan/           # Manuel subnet scan tetikle

# Dashboard
GET    /api/v1/dashboard/                   # Genel ozet istatistikler
GET    /api/v1/dashboard/timeline/          # Blacklist trend (son 30 gun)
GET    /api/v1/dashboard/worst-subnets/     # En cok blacklisted subnet'ler
```

#### 5.2 Ornek Response'lar

```json
// GET /api/v1/subnets/summary/
{
  "total_subnets": 150,
  "total_ips": 72448,
  "blacklisted_ips": 23,
  "clean_ips": 72425,
  "blacklist_rate": 0.032,
  "last_scan": {
    "job_id": 456,
    "type": "sampling",
    "completed_at": "2026-03-23T08:00:00Z",
    "duration_seconds": 245
  },
  "by_prefix": {
    "/22": {"count": 12, "ips": 12288, "blacklisted": 5},
    "/24": {"count": 138, "ips": 35328, "blacklisted": 18}
  }
}
```

```json
// GET /api/v1/subnets/{id}/status/
{
  "subnet_id": "uuid-here",
  "cidr": "109.236.48.0/22",
  "total_ips": 1024,
  "blacklisted_ips": 3,
  "clean_ips": 1021,
  "blacklist_rate": 0.0029,
  "worst_providers": ["spamhaus", "barracuda"],
  "blacklisted_details": [
    {
      "ip": "109.236.49.15",
      "providers": [{"provider": "spamhaus", "categories": ["spam"]}],
      "first_detected": "2026-03-20T10:00:00Z",
      "last_checked": "2026-03-23T08:00:00Z"
    }
  ],
  "last_scanned_at": "2026-03-23T08:00:00Z"
}
```

- [ ] Subnet listing endpoint (Supabase read)
- [ ] Subnet summary endpoint (aggregate from subnet_status)
- [ ] Scan trigger endpoint (Celery task dispatch)
- [ ] Scan job listing + detail
- [ ] Subnet-level results endpoint
- [ ] Dashboard istatistik endpoint'leri
- [ ] API versioning: `/api/v1/` prefix

---

### Sprint 6 — Frontend Guncellemeleri (2-3 gun)

**Amac:** Production build, subnet monitoring UI, landing redirect.

#### 6.1 Production Build

```dockerfile
# packages/frontend/Dockerfile (multi-stage)

FROM node:18-alpine AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

#### 6.2 Yeni Sayfalar

- [ ] `/subnets` — Subnet listesi tablo: CIDR, IP sayisi, blacklisted, rate, son tarama
- [ ] `/subnets/:id` — Subnet detay: IP listesi, blacklisted IP'ler, trend grafigi
- [ ] `/scans` — Scan job gecmisi: tip, durum, sure, sonuc
- [ ] `/settings/api-keys` — API key olusturma/silme
- [ ] `/settings/webhooks` — Webhook yonetimi
- [ ] `/settings/alerts` — Alert kural yonetimi

#### 6.3 Dashboard Guncellemesi

Mevcut dashboard'a eklenecekler:
- Toplam subnet/IP sayisi kartlari
- Blacklist rate gauge/trend
- Son scan durumu
- En kotu 5 subnet listesi

#### 6.4 Landing Page Redirect

```javascript
// routes/index.jsx
<Route path="/" element={<Navigate to="https://subnetkirala.com" replace />} />
```

- [ ] Multi-stage Dockerfile (yarn build → nginx)
- [ ] nginx.conf (SPA fallback + gzip + cache headers)
- [ ] Subnet monitoring sayfalari
- [ ] Dashboard guncellemesi
- [ ] API key / webhook / alert yonetim sayfalari
- [ ] Landing page → subnetkirala.com redirect
- [ ] Branding: AbuseBox → Blacklistify (logo, title, favicon)

---

### Sprint 7 — Ripefy Entegrasyonu + Go Live (1-2 gun)

**Amac:** Ripefy rehberini guncelle, Coolify'a deploy et, ilk scan'i calistir.

- [ ] `docs/ripefy-integration.md` — API key auth ile guncelle
- [ ] Ripefy icin API key olustur
- [ ] Ripefy icin webhook setup (blacklist.detected, scan.completed)
- [ ] Coolify deployment: docker-compose olarak deploy
- [ ] Domain: `blacklistify.subnetpanel.com` (veya mevcut `abox.subnetpanel.com`)
- [ ] Ilk sampling scan tetikle
- [ ] Sonuclari dogrula
- [ ] Ripefy developer ekibine entegrasyon dokumani ilet

---

## 6. Yeni Dependency Listesi (Toplam)

```
# Mevcut (korunacak)
fastapi==0.115.6
uvicorn==0.32.1
sqlalchemy==2.0.36
passlib==1.7.4
python-jose[cryptography]==3.4.0
pydantic==2.10.3
requests==2.32.3

# Yeni (eklenecek)
asyncpg==0.30.0              # Supabase PostgreSQL async driver
psycopg2-binary==2.9.10      # PostgreSQL sync driver (Alembic icin)
alembic==1.14.0               # DB migrations (blacklistify schema)
supabase==2.11.0              # Supabase Python client (Ripefy tablo okuma)
celery==5.4.0                 # Task queue + beat scheduler
redis==5.2.0                  # Cache + Celery broker
aiodns==3.2.0                 # Async DNS resolver
httpx==0.28.0                 # Async HTTP client (webhook delivery)
```

---

## 7. Environment Variables

```env
# Supabase (Ripefy'in mevcut instance'i)
SUPABASE_DB_URL=postgresql://blacklistify_app:password@db.xxxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs...

# Redis (Blacklistify local)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# App
APP_SECRET_KEY=change-me-in-production
APP_DEBUG=false
APP_CORS_ALLOWED_ORIGINS=https://blacklistify.subnetpanel.com

# Auth
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30
REFRESH_TOKEN_DAYS=14

# Admin
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=change-me
DEFAULT_ADMIN_EMAIL=admin@subnetpanel.com

# External
ABUSEIPDB_API_KEY=your-key-here

# Scanning
SCAN_INTERVAL_HOURS=6
SCAN_BATCH_SIZE=50
SCAN_CONCURRENCY=100
SCAN_CACHE_TTL_HOURS=6
```

---

## 8. Coolify Deployment

Mevcut Coolify'da AbuseBox backend + frontend ayri uygulama. Gecis plani:

1. Mevcut `abusebox-backend` ve `abusebox-frontend` uygulamalarini **durdur** (silme, rollback icin)
2. Yeni **Docker Compose** uygulamasi olustur: `blacklistify`
3. Repo: `subnetpanel/blacklistify`, branch: `main`
4. Servisler: redis, backend, worker, beat, frontend
5. Domain: `blacklistify.subnetpanel.com` → frontend (nginx :80)
6. Backend internal (frontend nginx uzerinden `/api/` proxy)
7. Environment variables: Supabase credentials + Redis + App secrets
8. Eski AbuseBox uygulamalarini dogruladiktan sonra sil

---

## 9. Zaman Cizelgesi

| Sprint | Icerik | Sure |
|--------|--------|------|
| 0 | Fork + monorepo gecisi | 1-2 gun |
| 1 | Supabase entegrasyonu + schema | 2-3 gun |
| 2 | Celery scheduler + background scanning | 3-4 gun |
| 3 | Async DNSBL engine | 2-3 gun |
| 4 | API key auth + webhook | 2 gun |
| 5 | Scan API endpoint'leri | 2 gun |
| 6 | Frontend guncellemeleri | 2-3 gun |
| 7 | Ripefy entegrasyonu + go live | 1-2 gun |
| **Toplam** | | **15-21 gun** |

---

## 10. Riskler ve Azaltma Stratejileri

| Risk | Olasilik | Etki | Azaltma |
|------|----------|------|---------|
| DNSBL provider ban | Yuksek | Eksik tarama sonuclari | Rate limiting, cache, batch delay |
| Supabase connection limit | Orta | Backend baglanti hatasi | Pooler mode, connection limiti ayarla |
| Ripefy tablo yapisi degisirse | Dusuk | subnet_reader bozulur | Stabil kolonlara baglan, monitoring ekle |
| 70K IP scan suresi | Orta | Guncel olmayan veri | Sampling stratejisi, 6 saatlik cycle |
| Celery worker crash | Orta | Tarama durur | Auto-restart, health check, dead letter queue |
| AbuseIPDB API limit | Yuksek | Sorgu basarisiz | Cache, gunluk limit takibi, fallback |
| Supabase downtime | Dusuk | Tum sistem durur | Health check, retry logic, graceful degradation |
