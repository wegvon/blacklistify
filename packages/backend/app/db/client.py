"""
Unified Supabase client for ALL database operations.
No direct PostgreSQL connection — everything goes through REST API (IPv4).

Uses service_role key for full table access.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Get the shared Supabase client (singleton)."""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    return create_client(settings.supabase_url, settings.supabase_service_key)


class SupabaseDB:
    """Wrapper for all Blacklistify table operations via Supabase REST API."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase()
        return self._client

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def insert(self, table: str, data: dict) -> dict:
        result = self.client.table(table).insert(data).execute()
        return result.data[0] if result.data else {}

    def insert_many(self, table: str, rows: list[dict]) -> list[dict]:
        if not rows:
            return []
        result = self.client.table(table).insert(rows).execute()
        return result.data or []

    def select(self, table: str, columns: str = "*", **filters) -> list[dict]:
        query = self.client.table(table).select(columns)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.execute()
        return result.data or []

    def select_one(self, table: str, columns: str = "*", **filters) -> dict | None:
        query = self.client.table(table).select(columns)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.limit(1).execute()
        if result and result.data:
            return result.data[0]
        return None

    def update(self, table: str, filters: dict, data: dict) -> list[dict]:
        query = self.client.table(table).update(data)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.execute()
        return result.data or []

    def delete(self, table: str, **filters) -> None:
        query = self.client.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        query.execute()

    def rpc(self, function_name: str, params: dict = None) -> any:
        """Call a PostgreSQL function via Supabase RPC."""
        result = self.client.rpc(function_name, params or {}).execute()
        return result.data

    # ------------------------------------------------------------------
    # Users (blf_users)
    # ------------------------------------------------------------------

    def get_user_by_username(self, username: str) -> dict | None:
        return self.select_one("blf_users", username=username)

    def get_user_by_id(self, user_id: int) -> dict | None:
        return self.select_one("blf_users", id=user_id)

    def create_user(self, username: str, email: str, phone: str, hashed_password: str, **kwargs) -> dict:
        return self.insert("blf_users", {
            "username": username,
            "email": email,
            "phone_number": phone,
            "hashed_password": hashed_password,
            **kwargs,
        })

    # ------------------------------------------------------------------
    # Hostnames (blf_hostnames) — legacy feature
    # ------------------------------------------------------------------

    def get_hostnames_by_user(self, user_id: int) -> list[dict]:
        return self.select("blf_hostnames", user_id=user_id)

    def create_hostname(self, data: dict) -> dict:
        return self.insert("blf_hostnames", data)

    def delete_hostname(self, hostname_id: int) -> None:
        self.delete("blf_hostnames", id=hostname_id)

    # ------------------------------------------------------------------
    # Scan Jobs (blf_scan_jobs)
    # ------------------------------------------------------------------

    def create_scan_job(self, data: dict) -> dict:
        return self.insert("blf_scan_jobs", data)

    def update_scan_job(self, job_id: int, data: dict) -> list[dict]:
        return self.update("blf_scan_jobs", {"id": job_id}, data)

    def get_scan_job(self, job_id: int) -> dict | None:
        return self.select_one("blf_scan_jobs", id=job_id)

    def list_scan_jobs(self, limit: int = 20, status: str | None = None) -> list[dict]:
        query = self.client.table("blf_scan_jobs").select("*").order("created_at", desc=True).limit(limit)
        if status:
            query = query.eq("status", status)
        return query.execute().data or []

    # ------------------------------------------------------------------
    # Scan Results (blf_scan_results)
    # ------------------------------------------------------------------

    def insert_scan_results(self, rows: list[dict]) -> list[dict]:
        return self.insert_many("blf_scan_results", rows)

    def get_results_by_job(self, job_id: int, blacklisted_only: bool = False, limit: int = 100) -> list[dict]:
        query = (
            self.client.table("blf_scan_results")
            .select("*")
            .eq("scan_job_id", job_id)
            .order("checked_at", desc=True)
            .limit(limit)
        )
        if blacklisted_only:
            query = query.eq("is_blacklisted", True)
        return query.execute().data or []

    def get_results_by_block(self, block_id: str, blacklisted_only: bool = False, limit: int = 100) -> list[dict]:
        query = (
            self.client.table("blf_scan_results")
            .select("*")
            .eq("block_id", block_id)
            .order("checked_at", desc=True)
            .limit(limit)
        )
        if blacklisted_only:
            query = query.eq("is_blacklisted", True)
        return query.execute().data or []

    # ------------------------------------------------------------------
    # Block Status (blf_block_status)
    # ------------------------------------------------------------------

    def get_all_block_statuses(self) -> list[dict]:
        return self.select("blf_block_status")

    def get_block_status(self, block_id: str) -> dict | None:
        return self.select_one("blf_block_status", block_id=block_id)

    def upsert_block_status(self, data: dict) -> dict:
        result = self.client.table("blf_block_status").upsert(data, on_conflict="block_id").execute()
        return result.data[0] if result.data else {}

    def get_worst_blocks(self, limit: int = 10) -> list[dict]:
        return (
            self.client.table("blf_block_status")
            .select("*")
            .gt("blacklisted_ips", 0)
            .order("blacklist_rate", desc=True)
            .limit(limit)
            .execute()
            .data or []
        )

    # ------------------------------------------------------------------
    # API Keys (blf_api_keys)
    # ------------------------------------------------------------------

    def create_api_key(self, data: dict) -> dict:
        return self.insert("blf_api_keys", data)

    def get_api_key_by_prefix(self, prefix: str) -> dict | None:
        return self.select_one("blf_api_keys", key_prefix=prefix, is_active=True)

    def list_api_keys(self) -> list[dict]:
        return self.select("blf_api_keys", is_active=True)

    def deactivate_api_key(self, key_id: int) -> None:
        self.update("blf_api_keys", {"id": key_id}, {"is_active": False})

    def update_api_key_used(self, key_id: int) -> None:
        from datetime import datetime, timezone
        self.update("blf_api_keys", {"id": key_id}, {"last_used_at": datetime.now(timezone.utc).isoformat()})

    # ------------------------------------------------------------------
    # Webhooks (blf_webhooks)
    # ------------------------------------------------------------------

    def create_webhook(self, data: dict) -> dict:
        return self.insert("blf_webhooks", data)

    def list_webhooks(self) -> list[dict]:
        return self.select("blf_webhooks")

    def get_webhook(self, webhook_id: int) -> dict | None:
        return self.select_one("blf_webhooks", id=webhook_id)

    def update_webhook(self, webhook_id: int, data: dict) -> list[dict]:
        return self.update("blf_webhooks", {"id": webhook_id}, data)

    def delete_webhook(self, webhook_id: int) -> None:
        self.delete("blf_webhooks", id=webhook_id)

    # ------------------------------------------------------------------
    # Alert Rules (blf_alert_rules)
    # ------------------------------------------------------------------

    def create_alert_rule(self, data: dict) -> dict:
        return self.insert("blf_alert_rules", data)

    def list_alert_rules(self, active_only: bool = False) -> list[dict]:
        if active_only:
            return self.select("blf_alert_rules", is_active=True)
        return self.select("blf_alert_rules")

    def delete_alert_rule(self, rule_id: int) -> None:
        self.delete("blf_alert_rules", id=rule_id)

    # ------------------------------------------------------------------
    # Ripefy tables (READ ONLY)
    # ------------------------------------------------------------------

    def get_all_prefixes(self) -> list[dict]:
        return (
            self.client.table("ip_prefixes")
            .select("id, ripe_account_id, cidr, is_test, description, created_at")
            .eq("is_test", False)
            .execute()
            .data or []
        )

    def get_all_blocks(self, status: str | None = None) -> list[dict]:
        query = self.client.table("ip_blocks").select("id, prefix_id, cidr, status, current_lease_id, notes, created_at")
        if status:
            query = query.eq("status", status)
        return query.execute().data or []

    def get_block_by_id(self, block_id: str) -> dict | None:
        return (
            self.client.table("ip_blocks")
            .select("id, prefix_id, cidr, status, current_lease_id, notes")
            .eq("id", block_id)
            .maybe_single()
            .execute()
            .data
        )

    def get_prefix_by_id(self, prefix_id: str) -> dict | None:
        return (
            self.client.table("ip_prefixes")
            .select("id, cidr, ripe_account_id, description")
            .eq("id", prefix_id)
            .maybe_single()
            .execute()
            .data
        )

    def get_customers(self) -> list[dict]:
        return self.client.table("customers").select("id, name, internal_code").execute().data or []


# Singleton
db = SupabaseDB()
