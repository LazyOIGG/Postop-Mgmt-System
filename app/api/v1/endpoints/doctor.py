from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict

from app.core.security import get_current_user
from app.models.schemas import DoctorMessageRequest, AlertProcessRequest
from app.services.doctor_service import doctor_service

router = APIRouter()


@router.get("/patients")
async def doctor_get_patients(user: Dict = Depends(get_current_user)):
    data = doctor_service.get_patient_list()
    return {"success": True, "patients": data}


@router.get("/high-risk")
async def doctor_get_high_risk(user: Dict = Depends(get_current_user)):
    data = doctor_service.get_high_risk_records()
    return {"success": True, "records": data}


@router.get("/abnormal-checkins")
async def doctor_get_abnormal_checkins(user: Dict = Depends(get_current_user)):
    data = doctor_service.get_abnormal_checkins()
    return {"success": True, "records": data}


@router.get("/patient-detail")
async def doctor_get_patient_detail(
    username: str = Query(...),
    user: Dict = Depends(get_current_user)
):
    data = doctor_service.get_patient_detail(username)
    if not data:
        raise HTTPException(status_code=404, detail="未找到患者详情")
    return {"success": True, "data": data}


@router.get("/alerts")
async def doctor_get_alerts(
    status: str = Query(None),
    user: Dict = Depends(get_current_user)
):
    data = doctor_service.get_alerts(status=status)
    return {"success": True, "alerts": data}


@router.post("/alerts/process")
async def doctor_process_alert(
    request: AlertProcessRequest,
    user: Dict = Depends(get_current_user)
):
    ok = doctor_service.process_alert(request.alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="告警记录不存在")
    return {"success": True, "message": "告警已处理"}


@router.post("/message")
async def doctor_send_message(
    request: DoctorMessageRequest,
    user: Dict = Depends(get_current_user)
):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    result = doctor_service.send_message(
        doctor_username=user["username"],
        patient_username=request.patient_username,
        content=request.content.strip()
    )
    return {"success": True, "message": result}
