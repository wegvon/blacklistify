"""
Read-only client for Ripefy's Supabase public schema.
Only SELECT operations — never modifies Ripefy data.

Real DB structure (discovered from live Supabase):
  ripe_accounts (id, name, code)
    └── ip_prefixes (id, ripe_account_id, cidr[/22], is_test, description)
          └── ip_blocks (id, prefix_id, cidr[/24], status[free|leased], current_lease_id)
                └── ip_leases (id, block_id, customer_id, channel_id, start_at, end_at, status[active|ended])
                      └── customers (id, name, internal_code, note)
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set to read Ripefy data"
            )
        from supabase import create_client
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


class SubnetReader:
    """Reads IP prefix/block data from Ripefy's Supabase (READ ONLY)."""

    # ------------------------------------------------------------------
    # ip_prefixes (/22 subnets — top-level allocation)
    # ------------------------------------------------------------------

    def get_all_prefixes(self) -> list[dict]:
        """Return all IP prefixes (excluding test prefixes)."""
        client = _get_client()
        result = (
            client.table("ip_prefixes")
            .select("id, ripe_account_id, cidr, is_test, description, created_at")
            .eq("is_test", False)
            .execute()
        )
        return result.data or []

    def get_prefix_by_id(self, prefix_id: str) -> dict | None:
        """Return a single prefix by UUID."""
        client = _get_client()
        result = (
            client.table("ip_prefixes")
            .select("id, ripe_account_id, cidr, is_test, description, created_at")
            .eq("id", prefix_id)
            .maybe_single()
            .execute()
        )
        return result.data

    # ------------------------------------------------------------------
    # ip_blocks (/24 blocks — the actual scan unit)
    # ------------------------------------------------------------------

    def get_all_blocks(self, status: str | None = None) -> list[dict]:
        """Return all IP blocks. Optionally filter by status (free|leased)."""
        client = _get_client()
        query = client.table("ip_blocks").select(
            "id, prefix_id, cidr, status, current_lease_id, notes, created_at"
        )
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return result.data or []

    def get_blocks_by_prefix(self, prefix_id: str) -> list[dict]:
        """Return all /24 blocks under a /22 prefix."""
        client = _get_client()
        result = (
            client.table("ip_blocks")
            .select("id, prefix_id, cidr, status, current_lease_id, notes, created_at")
            .eq("prefix_id", prefix_id)
            .execute()
        )
        return result.data or []

    def get_block_by_id(self, block_id: str) -> dict | None:
        """Return a single block by UUID."""
        client = _get_client()
        result = (
            client.table("ip_blocks")
            .select("id, prefix_id, cidr, status, current_lease_id, notes, created_at")
            .eq("id", block_id)
            .maybe_single()
            .execute()
        )
        return result.data

    # ------------------------------------------------------------------
    # Enriched queries (JOINs via Supabase)
    # ------------------------------------------------------------------

    def get_blocks_with_lease_info(self) -> list[dict]:
        """Return all blocks with customer/lease info (for dashboard)."""
        client = _get_client()
        result = (
            client.table("ip_blocks")
            .select(
                "id, prefix_id, cidr, status, notes, created_at, "
                "ip_prefixes!inner(cidr, ripe_account_id), "
                "ip_leases(id, customer_id, status, customers(name))"
            )
            .execute()
        )
        return result.data or []

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def get_prefix_count(self) -> int:
        """Return total number of non-test prefixes."""
        client = _get_client()
        result = (
            client.table("ip_prefixes")
            .select("id", count="exact")
            .eq("is_test", False)
            .execute()
        )
        return result.count or 0

    def get_block_count(self, status: str | None = None) -> int:
        """Return total number of blocks."""
        client = _get_client()
        query = client.table("ip_blocks").select("id", count="exact")
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return result.count or 0

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def get_customer_by_id(self, customer_id: str) -> dict | None:
        """Return a customer by UUID."""
        client = _get_client()
        result = (
            client.table("customers")
            .select("id, name, internal_code, note")
            .eq("id", customer_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def get_all_customers(self) -> list[dict]:
        """Return all customers."""
        client = _get_client()
        result = (
            client.table("customers")
            .select("id, name, internal_code")
            .execute()
        )
        return result.data or []


subnet_reader = SubnetReader()
