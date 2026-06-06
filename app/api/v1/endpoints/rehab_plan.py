from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional

from app.core.security import get_current_user
from app.models.schemas import (
    RehabPlanGenerateRequest, RehabPlanTaskCompleteRequest, RehabPlanUpdatePhaseRequest
)
from app.services.rehab_plan_service import rehab_plan_service

router = APIRouter()


@router.post("/generate")
async def generate_rehab_plan(
    request: RehabPlanGenerateRequest,
    user: Dict = Depends(get_current_user)
):
    """AI 生成个性化康复计划"""
    username = user["username"]
    result = await rehab_plan_service.generate_plan(
        username=username,
        surgery_type=request.surgery_type,
        plan_title=request.plan_title or ""
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "生成计划失败"))
    return result


@router.get("/")
async def get_my_plans(
    status: Optional[str] = Query(None, description="过滤状态: active/completed/cancelled"),
    user: Dict = Depends(get_current_user)
):
    """获取用户的所有康复计划"""
    username = user["username"]
    plans = rehab_plan_service.get_user_plans(username, status)
    return {"success": True, "plans": plans}


@router.get("/tasks/today")
async def get_today_tasks(user: Dict = Depends(get_current_user)):
    """获取今日康复任务"""
    username = user["username"]
    tasks = rehab_plan_service.get_today_tasks(username)
    return {"success": True, "tasks": tasks, "date": __import__("datetime").datetime.now().strftime("%Y-%m-%d")}


@router.get("/{plan_id}")
async def get_plan_detail(
    plan_id: int,
    user: Dict = Depends(get_current_user)
):
    """获取康复计划详情（含所有任务按阶段分组）"""
    detail = rehab_plan_service.get_plan_detail(plan_id)
    if not detail:
        raise HTTPException(status_code=404, detail="康复计划不存在")
    if detail.get("username") != user["username"]:
        raise HTTPException(status_code=403, detail="无权查看此计划")
    return {"success": True, "plan": detail}


@router.post("/tasks/complete")
async def complete_task(
    request: RehabPlanTaskCompleteRequest,
    user: Dict = Depends(get_current_user)
):
    """标记康复任务为已完成"""
    result = rehab_plan_service.complete_task(user["username"], request.task_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))
    return result


@router.put("/{plan_id}/phase")
async def advance_plan_phase(
    plan_id: int,
    request: RehabPlanUpdatePhaseRequest,
    user: Dict = Depends(get_current_user)
):
    """推进康复计划到下一阶段"""
    plan = rehab_plan_service.get_plan_detail(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="康复计划不存在")
    if plan.get("username") != user["username"]:
        raise HTTPException(status_code=403, detail="无权操作此计划")
    ok = rehab_plan_service.advance_phase(plan_id, request.current_phase)
    if not ok:
        raise HTTPException(status_code=400, detail="阶段推进失败，可能阶段名无效或已处于更后阶段")
    return {"success": True, "message": f"已推进至{request.current_phase}", "current_phase": request.current_phase}


@router.delete("/{plan_id}")
async def cancel_plan(
    plan_id: int,
    user: Dict = Depends(get_current_user)
):
    """取消康复计划及所有关联提醒"""
    plan = rehab_plan_service.get_plan_detail(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="康复计划不存在")
    if plan.get("username") != user["username"]:
        raise HTTPException(status_code=403, detail="无权操作此计划")
    ok = rehab_plan_service.cancel_plan(plan_id, user["username"])
    if not ok:
        raise HTTPException(status_code=500, detail="取消计划失败")
    return {"success": True, "message": "康复计划已取消"}


@router.get("/{plan_id}/dashboard")
async def get_plan_dashboard(
    plan_id: int,
    user: Dict = Depends(get_current_user)
):
    """获取康复计划仪表盘聚合数据"""
    plan = rehab_plan_service.get_plan_detail(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="康复计划不存在")
    if plan.get("username") != user["username"]:
        raise HTTPException(status_code=403, detail="无权查看此计划")
    return rehab_plan_service.get_dashboard_data(plan_id)


@router.get("/{plan_id}/calendar")
async def get_plan_calendar(
    plan_id: int,
    year: int = Query(...),
    month: int = Query(...),
    user: Dict = Depends(get_current_user)
):
    """获取康复计划月度日历热力图数据"""
    plan = rehab_plan_service.get_plan_detail(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="康复计划不存在")
    if plan.get("username") != user["username"]:
        raise HTTPException(status_code=403, detail="无权查看此计划")
    return rehab_plan_service.get_calendar_data(plan_id, year, month)
