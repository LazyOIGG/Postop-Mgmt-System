from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Optional
from app.core.security import get_current_user
from app.db.session import db_instance

router = APIRouter()


@router.get("/unread-count")
async def get_unread_notification_count(user: Dict = Depends(get_current_user)):
    count = db_instance.get_unread_notification_count(user["username"])
    return {"success": True, "count": count}


@router.get("")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    user: Dict = Depends(get_current_user),
):
    notifications = db_instance.get_notifications(
        user["username"], unread_only=unread_only, limit=limit
    )
    return {"success": True, "notifications": notifications, "count": len(notifications)}


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int, user: Dict = Depends(get_current_user)
):
    ok = db_instance.mark_notification_read(notification_id, user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"success": True}


@router.put("/read-all")
async def mark_all_notifications_read(user: Dict = Depends(get_current_user)):
    db_instance.mark_all_notifications_read(user["username"])
    return {"success": True}
