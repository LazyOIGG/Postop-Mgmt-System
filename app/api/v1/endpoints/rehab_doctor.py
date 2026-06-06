from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional
from app.core.security import get_current_user
from app.models.schemas import DoctorRehabFeedback
from app.services.rehab_doctor_service import rehab_doctor_service

router = APIRouter()


@router.get("/patients/{username}/rehab")
async def get_patient_rehab(
    username: str,
    user: Dict = Depends(get_current_user)
):
    """医生查看患者康复全貌"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="仅医生可查看")
    result = rehab_doctor_service.get_patient_rehab_overview(username)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/patients/{username}/rehab/metrics")
async def get_patient_rehab_metrics(
    username: str,
    metric_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: Dict = Depends(get_current_user)
):
    """医生查看患者指标趋势"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="仅医生可查看")
    result = rehab_doctor_service.get_patient_metrics(
        username, metric_type, date_from, date_to)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/patients/{username}/rehab/feedback")
async def send_rehab_feedback(
    username: str,
    request: DoctorRehabFeedback,
    user: Dict = Depends(get_current_user)
):
    """医生给患者发送康复反馈"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="仅医生可发送反馈")
    result = rehab_doctor_service.send_feedback(
        doctor_username=user["username"],
        patient_username=username,
        plan_id=request.plan_id,
        feedback_content=request.feedback_content
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
