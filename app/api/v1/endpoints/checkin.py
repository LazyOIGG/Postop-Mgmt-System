from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from app.core.security import get_current_user
from app.models.schemas import DailyCheckinRequest
from app.db.session import db_instance
from app.services.checkin_service import checkin_service
from app.services.anomaly_service import anomaly_service
from app.services.notification_service import notification_service

router = APIRouter()


async def _handle_abnormal_alert(username: str, abnormal_reason: str):
    """打卡异常时创建告警并推送 WebSocket 到医生端"""
    profile = db_instance.get_patient_profile(username)
    real_name = profile.get("real_name", "") if profile else ""

    db_instance.create_alert_notification(
        username=username,
        real_name=real_name,
        risk_level="打卡异常",
        risk_reasons=abnormal_reason,
        advice="患者打卡出现异常指标，请及时关注",
        source_type="checkin",
    )

    # 推送 WebSocket 到所有在线医生
    admins = db_instance.get_admin_usernames()
    for admin in admins:
        await notification_service.notify_alert(admin, {
            "username": username,
            "real_name": real_name,
            "risk_level": "打卡异常",
            "reason": abnormal_reason,
        })


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

    # 打卡异常时触发告警
    if analysis["abnormal_flag"] == 1:
        await _handle_abnormal_alert(username, analysis["abnormal_reason"])

    # 检查连续异常趋势
    if anomaly_service.check_consecutive_abnormal(username, days=3):
        profile = db_instance.get_patient_profile(username)
        real_name = profile.get("real_name", "") if profile else ""
        db_instance.create_alert_notification(
            username=username,
            real_name=real_name,
            risk_level="连续异常",
            risk_reasons="连续 3 天打卡出现异常指标",
            advice="患者连续多天打卡异常，建议主动联系了解情况",
            source_type="checkin",
        )
        admins = db_instance.get_admin_usernames()
        for admin in admins:
            await notification_service.notify_alert(admin, {
                "username": username,
                "real_name": real_name,
                "risk_level": "连续异常",
                "reason": "连续 3 天打卡出现异常指标",
            })

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