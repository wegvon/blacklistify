from pydantic import BaseModel


class SubnetResponse(BaseModel):
    id: str
    cidr: str
    description: str | None = None
    status: str
    customer_id: str | None = None


class SubnetStatusResponse(BaseModel):
    subnet_id: str
    subnet_cidr: str
    total_ips: int = 0
    blacklisted_ips: int = 0
    clean_ips: int = 0
    blacklist_rate: float = 0.0
    worst_providers: list[str] = []
    last_scanned_at: str | None = None


class SubnetSummaryResponse(BaseModel):
    total_subnets: int = 0
    total_ips: int = 0
    blacklisted_ips: int = 0
    clean_ips: int = 0
    blacklist_rate: float = 0.0
    last_scan: dict | None = None
