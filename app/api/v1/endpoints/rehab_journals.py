from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional
from app.core.security import get_current_user
from app.models.schemas import RehabJournalCreate
from app.services.rehab_journal_service import rehab_journal_service

router = APIRouter()


@router.post("/{plan_id}/journals")
async def create_journal(
    plan_id: int, request: RehabJournalCreate,
    user: Dict = Depends(get_current_user)
):
    result = rehab_journal_service.save_journal(
        user["username"], plan_id, request.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/{plan_id}/journals")
async def get_journals(
    plan_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: Dict = Depends(get_current_user)
):
    return rehab_journal_service.get_journals(plan_id, date_from, date_to)


@router.get("/{plan_id}/journals/{journal_id}")
async def get_journal(
    plan_id: int, journal_id: int,
    user: Dict = Depends(get_current_user)
):
    result = rehab_journal_service.get_journal(journal_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
