from pydantic import BaseModel


class PrefixResponse(BaseModel):
    """Ripefy ip_prefixes (/22 allocation)."""
    id: str
    ripe_account_id: str | None = None
    cidr: str
    is_test: bool = False
    description: str | None = None


class BlockResponse(BaseModel):
    """Ripefy ip_blocks (/24 block)."""
    id: str
    prefix_id: str
    cidr: str
    status: str  # free, leased
    current_lease_id: str | None = None
    notes: str | None = None


class BlockStatusResponse(BaseModel):
    """Blacklist status for a /24 block."""
    block_id: str
    block_cidr: str
    prefix_id: str | None = None
    prefix_cidr: str | None = None
    customer_name: str | None = None
    total_ips: int = 0
    blacklisted_ips: int = 0
    clean_ips: int = 0
    blacklist_rate: float = 0.0
    worst_providers: list[str] = []
    last_scanned_at: str | None = None


class SummaryResponse(BaseModel):
    """Aggregate blacklist summary across all blocks."""
    total_prefixes: int = 0
    total_blocks: int = 0
    total_ips: int = 0
    blacklisted_ips: int = 0
    clean_ips: int = 0
    blacklist_rate: float = 0.0
    last_scan: dict | None = None
