from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.client import db
from app.schemas import DelistRequest
from app.services.dnsbl import check_dnsbl_providers

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.get("/quick-check/")
def quick_check(hostname: str | None = None):
    if hostname is None or hostname.strip() == "":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide a Hostname")

    result = check_dnsbl_providers(hostname)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.post("/delist/")
def delist(payload: DelistRequest, user: dict = Depends(get_current_user)):
    history_id = payload.delist_required_data.get("id")
    if history_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing delist check history id")

    history = db.select_one("blf_check_histories", id=history_id)
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check history not found")

    # Verify ownership
    hostname = db.select_one("blf_hostnames", id=history["hostname_id"])
    if not hostname or hostname.get("user_id") != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check history not found")

    if payload.provider != "b.barracudacentral.org":
        return {"msg": "Not implemented"}

    result = dict(history.get("result") or {})
    detected = result.get("detected_on", [])
    for item in detected:
        if item.get("provider") == payload.provider:
            item["status"] = "closed"
            item["response"] = "queued"

    result["detected_on"] = detected
    db.update("blf_check_histories", {"id": history_id}, {
        "result": result,
        "updated": datetime.now(timezone.utc).isoformat(),
    })

    return {"msg": "success", "result": result}
