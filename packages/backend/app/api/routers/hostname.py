from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.security import get_current_user
from app.db.client import db
from app.schemas import (
    HostnameCreateRequest,
    HostnameListItem,
    HostnameResponse,
    HostnameUpdateRequest,
)
from app.services.dnsbl import check_dnsbl_providers

router = APIRouter(prefix="/hostname", tags=["hostname"])


def _to_response(h: dict) -> HostnameResponse:
    return HostnameResponse(
        id=h["id"],
        user=h["user_id"],
        hostname_type=h["hostname_type"],
        hostname=h["hostname"],
        description=h.get("description"),
        is_alert_enabled=h.get("is_alert_enabled", False),
        is_monitor_enabled=h.get("is_monitor_enabled", False),
        status=h.get("status", "active"),
        is_blacklisted=h.get("is_blacklisted", False),
        created=h.get("created"),
        updated=h.get("updated"),
    )


@router.post("/", response_model=HostnameResponse)
def create_hostname(payload: HostnameCreateRequest, user: dict = Depends(get_current_user)):
    existing = db.select("blf_hostnames", user_id=user["id"], hostname=payload.hostname)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hostname already exists")

    hostname = db.insert("blf_hostnames", {
        "user_id": user["id"],
        "hostname_type": payload.hostname_type,
        "hostname": payload.hostname,
        "description": payload.description,
        "is_alert_enabled": payload.is_alert_enabled,
        "is_monitor_enabled": payload.is_monitor_enabled,
        "status": "active",
    })

    check_result = check_dnsbl_providers(payload.hostname)
    if not check_result.get("error"):
        hostname_is_bl = bool(check_result.get("is_blacklisted", False))
        db.update("blf_hostnames", {"id": hostname["id"]}, {"is_blacklisted": hostname_is_bl})
        hostname["is_blacklisted"] = hostname_is_bl
        db.insert("blf_check_histories", {
            "hostname_id": hostname["id"],
            "result": check_result,
            "status": "current",
        })

    return _to_response(hostname)


@router.get("/list/", response_model=list[HostnameListItem])
def list_hostnames(user: dict = Depends(get_current_user)):
    hostnames = db.select("blf_hostnames", user_id=user["id"])

    output = []
    for h in hostnames:
        checks = db.select("blf_check_histories", hostname_id=h["id"])
        current_checks = [c for c in checks if c.get("status") == "current"]
        current_check = max(current_checks, key=lambda x: x.get("created", "")) if current_checks else None

        check_result = dict(current_check["result"]) if current_check and current_check.get("result") else None
        if check_result and current_check:
            check_result["id"] = current_check["id"]

        item = HostnameListItem(
            **_to_response(h).model_dump(),
            result=check_result,
            checked=current_check.get("created", "Not checked") if current_check else "Not checked",
        )
        output.append(item)

    return output


@router.get("/{pk}", response_model=HostnameResponse)
def get_hostname(pk: int, user: dict = Depends(get_current_user)):
    results = db.select("blf_hostnames", id=pk, user_id=user["id"])
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostname not found")
    return _to_response(results[0])


@router.put("/{pk}", response_model=HostnameResponse)
def update_hostname(pk: int, payload: HostnameUpdateRequest, user: dict = Depends(get_current_user)):
    results = db.select("blf_hostnames", id=pk, user_id=user["id"])
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostname not found")

    updated = db.update("blf_hostnames", {"id": pk}, {
        "hostname_type": payload.hostname_type,
        "hostname": payload.hostname,
        "description": payload.description,
        "is_alert_enabled": payload.is_alert_enabled,
        "is_monitor_enabled": payload.is_monitor_enabled,
        "status": payload.status,
    })
    return _to_response(updated[0] if updated else results[0])


@router.delete("/{pk}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hostname(pk: int, user: dict = Depends(get_current_user)):
    results = db.select("blf_hostnames", id=pk, user_id=user["id"])
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostname not found")
    db.delete("blf_hostnames", id=pk)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
