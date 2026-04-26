from fastapi import APIRouter, Depends, Query
from typing import Dict

from app.core.security import get_current_user
from app.services.overview_service import overview_service

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    days: int = Query(7, ge=3, le=30),
    user: Dict = Depends(get_current_user)
):
    username = user["username"]
    data = overview_service.build_dashboard(username=username, days=days)
    return {
        "success": True,
        "days": days,
        "data": data
    }