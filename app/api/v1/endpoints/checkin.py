from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from app.core.security import get_current_user
from app.models.schemas import DailyCheckinRequest
from app.db.session import db_instance
from app.services.checkin_service import checkin_service

router = APIRouter()


@router.post("/daily")
async def save_daily_checkin(
    request: DailyCheckinRequest,
    user: Dict = Depends(get_current_user)
):
    username = user["username"]

    analysis = checkin_service.analyze_checkin(request.dict())

    ok = db_instance.save_daily_checkin(
        username=username,
        checkin_date=request.checkin_date,
        symptoms=request.symptoms or "",
        temperature=request.temperature,
        blood_pressure=request.blood_pressure or "",
        blood_sugar=request.blood_sugar,
        heart_rate=request.heart_rate,
        sleep_status=request.sleep_status or "",
        diet_status=request.diet_status or "",
        exercise_status=request.exercise_status or "",
        medication_taken=1 if request.medication_taken else 0,
        note=request.note or "",
        abnormal_flag=analysis["abnormal_flag"],
        abnormal_reason=analysis["abnormal_reason"]
    )

    if not ok:
        raise HTTPException(status_code=500, detail="保存打卡失败")

    latest = db_instance.get_today_checkin(username, request.checkin_date)

    return {
        "success": True,
        "message": "打卡成功",
        "record": latest
    }


@router.get("/daily")
async def get_my_daily_checkins(user: Dict = Depends(get_current_user)):
    username = user["username"]
    records = db_instance.get_daily_checkins(username, limit=30)
    return {"success": True, "records": records}