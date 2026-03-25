"""
Async DNSBL checker using aiodns for high-throughput IP scanning.
Replaces the sync ThreadPoolExecutor approach for bulk operations.
"""

from __future__ import annotations

import asyncio
import logging
import time

import aiodns

from app.services.cache import RedisCache
from app.services.dnsbl import BASE_PROVIDERS
from app.core.config import settings

logger = logging.getLogger(__name__)


class AsyncDNSBLChecker:
    """High-performance async DNSBL checker."""

    def __init__(
        self,
        providers: list[str] | None = None,
        concurrency: int | None = None,
        timeout: float = 2.0,
        cache: RedisCache | None = None,
    ):
        self.providers = providers or BASE_PROVIDERS
        self.concurrency = concurrency or settings.scan_concurrency
        self.timeout = timeout
        self.cache = cache
        self._semaphore: asyncio.Semaphore | None = None

    async def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.concurrency)
        return self._semaphore

    async def check_ip(self, ip: str) -> dict:
        """Check a single IP against all DNSBL providers."""
        import sys
        print(f"DEBUG: check_ip called for {ip}", flush=True)
        # Check cache first
        if self.cache:
            cached = self.cache.get(f"dnsbl:{ip}")
            if cached is not None:
                return cached

        reversed_ip = ".".join(reversed(ip.split(".")))
        resolver = aiodns.DNSResolver(timeout=self.timeout)
        semaphore = await self._get_semaphore()

        tasks = [
            self._check_provider(resolver, semaphore, reversed_ip, provider)
            for provider in self.providers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        detected = []
        checked = 0
        errors = 0
        for r in results:
            if isinstance(r, Exception):
                errors += 1
                logger.warning("DNSBL check exception for %s: %s", ip, r)
                continue
            provider, is_listed = r
            checked += 1
            if is_listed:
                detected.append({"provider": provider, "status": "open"})

        if errors > 0:
            logger.warning("DNSBL check for %s: %d errors, %d checked, %d blacklisted",
                         ip, errors, checked, len(detected))

        result = {
            "ip": ip,
            "is_blacklisted": len(detected) > 0,
            "providers_detected": detected,
            "providers_total": checked,
        }

        # Store in cache
        if self.cache:
            self.cache.set(f"dnsbl:{ip}", result)

        return result

    async def check_batch(self, ips: list[str]) -> list[dict]:
        """Check multiple IPs in parallel."""
        import sys
        print(f"DEBUG: check_batch called with {len(ips)} IPs: {ips[:3]}...", flush=True)
        start = time.monotonic()
        tasks = [self.check_ip(ip) for ip in ips]
        results = await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start

        blacklisted = sum(1 for r in results if r.get("is_blacklisted"))
        logger.debug(
            "Batch check: %d IPs, %d blacklisted, %.1fs elapsed",
            len(ips), blacklisted, elapsed,
        )
        return results

    async def _check_provider(
        self,
        resolver: aiodns.DNSResolver,
        semaphore: asyncio.Semaphore,
        reversed_ip: str,
        provider: str,
    ) -> tuple[str, bool]:
        """Check a single IP against a single provider."""
        async with semaphore:
            try:
                await resolver.query(f"{reversed_ip}.{provider}", "A")
                return (provider, True)
            except aiodns.error.DNSError:
                return (provider, False)
            except Exception as e:
                logger.debug("DNS query failed for %s.%s: %s", reversed_ip, provider, e)
                return (provider, False)
