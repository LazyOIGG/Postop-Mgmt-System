from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict

from app.core.security import get_current_user
from app.services.doctor_service import doctor_service

router = APIRouter()


@router.get("/patients")
async def doctor_get_patients(user: Dict = Depends(get_current_user)):
    data = doctor_service.get_patient_list()
    return {
        "success": True,
        "patients": data
    }


@router.get("/high-risk")
async def doctor_get_high_risk(user: Dict = Depends(get_current_user)):
    data = doctor_service.get_high_risk_records()
    return {
        "success": True,
        "records": data
    }


@router.get("/abnormal-checkins")
async def doctor_get_abnormal_checkins(user: Dict = Depends(get_current_user)):
    data = doctor_service.get_abnormal_checkins()
    return {
        "success": True,
        "records": data
    }


@router.get("/patient-detail")
async def doctor_get_patient_detail(
    username: str = Query(...),
    user: Dict = Depends(get_current_user)
):
    data = doctor_service.get_patient_detail(username)
    if not data:
        raise HTTPException(status_code=404, detail="未找到患者详情")

    return {
        "success": True,
        "data": data
    }