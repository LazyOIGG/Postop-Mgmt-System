from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional
from app.core.security import get_current_user
from app.services.rehab_exercise_service import rehab_exercise_service

router = APIRouter()


@router.get("/rehab-exercises")
async def get_exercises(
    phase: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    surgery_type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    user: Dict = Depends(get_current_user)
):
    return rehab_exercise_service.get_exercises(
        phase=phase, category=category, surgery_type=surgery_type,
        difficulty=difficulty, search=search, limit=limit)


@router.get("/rehab-exercises/recommended")
async def get_recommended(
    surgery_type: Optional[str] = Query(None),
    current_phase: Optional[str] = Query("恢复期"),
    user: Dict = Depends(get_current_user)
):
    return rehab_exercise_service.get_recommended(surgery_type, current_phase)


@router.get("/rehab-exercises/{exercise_id}")
async def get_exercise_detail(
    exercise_id: int, user: Dict = Depends(get_current_user)
):
    result = rehab_exercise_service.get_exercise_detail(exercise_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
