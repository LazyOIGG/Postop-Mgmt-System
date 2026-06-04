from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.response import ApiResponse
from app.core.security import get_current_user
from app.db.session import db_instance

router = APIRouter()


@router.get("/unread-count")
async def get_unread_notification_count(user: Dict = Depends(get_current_user)):
    count = db_instance.get_unread_notification_count(user["username"])
    return ApiResponse.ok(data={"count": count}, message="获取未读通知数成功")


@router.get("")
async def get_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    limit: Optional[int] = Query(None, deprecated=True, description="已弃用，请使用 page/size"),
    user: Dict = Depends(get_current_user),
):
    """获取通知列表（支持分页，兼容旧版 limit 参数）"""
    # 兼容旧版 limit 参数
    if limit is not None:
        notifications = db_instance.get_notifications(
            user["username"], unread_only=unread_only, limit=limit
        )
        return ApiResponse.ok(data={"notifications": notifications, "count": len(notifications)})

    offset = (page - 1) * size
    notifications = db_instance.get_notifications_paginated(
        user["username"], unread_only=unread_only, limit=size, offset=offset
    )
    total = db_instance.get_notification_count(user["username"], unread_only=unread_only)
    return ApiResponse.paginated(items=notifications, total=total, page=page, page_size=size)


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int, user: Dict = Depends(get_current_user)
):
    """标记通知为已读"""
    ok = db_instance.mark_notification_read(notification_id, user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="通知不存在")
    return ApiResponse.ok(message="已标记为已读")


@router.put("/read-all")
async def mark_all_notifications_read(user: Dict = Depends(get_current_user)):
    """标记全部通知为已读"""
    db_instance.mark_all_notifications_read(user["username"])
    return ApiResponse.ok(message="已全部标记为已读")


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    user: Dict = Depends(get_current_user),
):
    """删除通知（仅通知所有者可删除）"""
    ok = db_instance.delete_notification(notification_id, user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="通知不存在或无权删除")
    return ApiResponse.ok(message="通知已删除")
