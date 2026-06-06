from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional
from app.core.security import get_current_user
from app.models.schemas import RehabMetricCreate
from app.services.rehab_metrics_service import rehab_metrics_service

router = APIRouter()


@router.post("/{plan_id}/metrics")
async def save_metric(
    plan_id: int, request: RehabMetricCreate,
    user: Dict = Depends(get_current_user)
):
    result = rehab_metrics_service.save_metric(
        user["username"], plan_id, request.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/{plan_id}/metrics")
async def get_metrics(
    plan_id: int,
    metric_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: Dict = Depends(get_current_user)
):
    return rehab_metrics_service.get_metrics(
        plan_id, metric_type, date_from, date_to)


@router.get("/{plan_id}/metrics/latest")
async def get_latest_metrics(
    plan_id: int, user: Dict = Depends(get_current_user)
):
    return rehab_metrics_service.get_latest_metrics(plan_id)


@router.get("/{plan_id}/metrics/trend")
async def get_metric_trend(
    plan_id: int,
    metric_type: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: Dict = Depends(get_current_user)
):
    return rehab_metrics_service.get_trend_data(
        plan_id, metric_type, date_from, date_to)
