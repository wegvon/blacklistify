from pydantic import BaseModel


class ScanTriggerRequest(BaseModel):
    job_type: str = "manual"  # manual, sampling, full, single
    subnet_id: str | None = None  # if single subnet scan


class ScanJobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    total_subnets: int = 0
    total_ips: int = 0
    scanned_ips: int = 0
    blacklisted_ips: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    created_at: str


class ScanResultResponse(BaseModel):
    id: int
    scan_job_id: int
    subnet_id: str | None = None
    subnet_cidr: str
    ip_address: str
    is_blacklisted: bool = False
    providers_detected: list[dict] = []
    providers_total: int = 0
    checked_at: str


class ScanResultSummary(BaseModel):
    total: int = 0
    blacklisted: int = 0
    clean: int = 0
    blacklist_rate: float = 0.0
