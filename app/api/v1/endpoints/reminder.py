from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from app.core.security import get_current_user
from app.models.schemas import ReminderCreateRequest, ReminderStatusUpdateRequest
from app.db.session import db_instance
from app.services.reminder_service import reminder_service

router = APIRouter()


@router.post("/")
async def create_reminder(
    request: ReminderCreateRequest,
    user: Dict = Depends(get_current_user)
):
    username = user["username"]

    ok = db_instance.save_reminder(
        username=username,
        reminder_type=request.reminder_type,
        title=request.title,
        description=request.description or "",
        reminder_date=request.reminder_date,
        reminder_time=request.reminder_time
    )

    if not ok:
        raise HTTPException(status_code=500, detail="创建提醒失败")

    reminders = reminder_service.get_all_reminders(username)
    stats = reminder_service.get_today_stats(username)

    return {
        "success": True,
        "message": "提醒创建成功",
        "reminders": reminders,
        "today_stats": stats
    }


@router.get("/")
async def get_my_reminders(user: Dict = Depends(get_current_user)):
    username = user["username"]
    reminders = reminder_service.get_all_reminders(username)
    stats = reminder_service.get_today_stats(username)

    return {
        "success": True,
        "reminders": reminders,
        "today_stats": stats
    }


@router.post("/status")
async def update_reminder_status(
    request: ReminderStatusUpdateRequest,
    user: Dict = Depends(get_current_user)
):
    username = user["username"]

    if request.status not in ["pending", "completed"]:
        raise HTTPException(status_code=400, detail="状态不合法")

    ok = db_instance.update_reminder_status(username, request.reminder_id, request.status)
    if not ok:
        raise HTTPException(status_code=500, detail="更新提醒状态失败")

    reminders = reminder_service.get_all_reminders(username)
    stats = reminder_service.get_today_stats(username)

    return {
        "success": True,
        "message": "提醒状态更新成功",
        "reminders": reminders,
        "today_stats": stats
    }


@router.delete("/{reminder_id}")
async def delete_my_reminder(
    reminder_id: int,
    user: Dict = Depends(get_current_user)
):
    username = user["username"]

    ok = db_instance.delete_reminder(username, reminder_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除提醒失败")

    reminders = reminder_service.get_all_reminders(username)
    stats = reminder_service.get_today_stats(username)

    return {
        "success": True,
        "message": "提醒删除成功",
        "reminders": reminders,
        "today_stats": stats
    }