from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from app.core.security import get_current_user
from app.models.schemas import PatientProfileUpdateRequest
from app.db.session import db_instance

router = APIRouter()


@router.get("/me")
async def get_my_profile(user: Dict = Depends(get_current_user)):
    username = user["username"]

    profile = db_instance.get_patient_profile(username)
    latest_assessment = db_instance.get_latest_health_assessment(username)

    return {
        "success": True,
        "profile": profile,
        "latest_assessment": latest_assessment
    }


@router.post("/me")
async def save_my_profile(
    request: PatientProfileUpdateRequest,
    user: Dict = Depends(get_current_user)
):
    username = user["username"]

    ok = db_instance.save_patient_profile(
        username=username,
        real_name=request.real_name or "",
        gender=request.gender or "",
        age=request.age,
        phone=request.phone or "",
        height=request.height,
        weight=request.weight,
        blood_type=request.blood_type or "",
        medical_history=request.medical_history or "",
        allergy_history=request.allergy_history or "",
        current_medications=request.current_medications or "",
        emergency_contact=request.emergency_contact or "",
        emergency_phone=request.emergency_phone or "",
        health_stage=request.health_stage or "长期管理"
    )

    if not ok:
        raise HTTPException(status_code=500, detail="保存健康档案失败")

    profile = db_instance.get_patient_profile(username)
    latest_assessment = db_instance.get_latest_health_assessment(username)

    return {
        "success": True,
        "profile": profile,
        "latest_assessment": latest_assessment
    }