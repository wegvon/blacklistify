"""
Read-only client for Ripefy's Supabase public schema.
Only SELECT operations — never modifies Ripefy data.
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
    """Reads subnet data from Ripefy's Supabase (READ ONLY)."""

    def get_active_subnets(self) -> list[dict]:
        """Return all active subnets from Ripefy."""
        client = _get_client()
        result = (
            client.table("subnets")
            .select("id, cidr, description, status, customer_id")
            .eq("status", "active")
            .execute()
        )
        return result.data or []

    def get_subnet_by_id(self, subnet_id: str) -> dict | None:
        """Return a single subnet by UUID."""
        client = _get_client()
        result = (
            client.table("subnets")
            .select("*")
            .eq("id", subnet_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def get_subnets_by_customer(self, customer_id: str) -> list[dict]:
        """Return all active subnets for a customer."""
        client = _get_client()
        result = (
            client.table("subnets")
            .select("id, cidr, description")
            .eq("customer_id", customer_id)
            .eq("status", "active")
            .execute()
        )
        return result.data or []

    def get_subnet_count(self) -> int:
        """Return the total number of active subnets."""
        client = _get_client()
        result = (
            client.table("subnets")
            .select("id", count="exact")
            .eq("status", "active")
            .execute()
        )
        return result.count or 0


subnet_reader = SubnetReader()
