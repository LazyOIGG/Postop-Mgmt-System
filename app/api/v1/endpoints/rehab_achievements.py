from fastapi import APIRouter, Depends
from typing import Dict
from app.core.security import get_current_user
from app.services.rehab_achievement_service import rehab_achievement_service

router = APIRouter()


@router.get("/rehab-achievements/defs")
async def get_all_defs(user: Dict = Depends(get_current_user)):
    return rehab_achievement_service.get_all_defs()


@router.get("/{plan_id}/achievements")
async def get_user_achievements(
    plan_id: int, user: Dict = Depends(get_current_user)
):
    return rehab_achievement_service.get_user_achievements(
        user["username"], plan_id)


@router.post("/{plan_id}/achievements/check")
async def check_achievements(
    plan_id: int, user: Dict = Depends(get_current_user)
):
    return rehab_achievement_service.check_and_award(
        user["username"], plan_id)
