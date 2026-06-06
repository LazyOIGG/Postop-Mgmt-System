from app.agents.tools.base import Tool
from app.agents.tools.registry import tool_registry
from app.services.rehab_plan_service import rehab_plan_service
from app.services.rehab_exercise_service import rehab_exercise_service
from app.services.rehab_metrics_service import rehab_metrics_service

# ── Tool schemas ──────────────────────────────────────────────────

GENERATE_REHAB_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "surgery_type": {
            "type": "string",
            "description": "手术类型（可选），如：阑尾切除术、膝关节置换术等。非术后患者可不提供，系统将生成通用健康管理计划"
        },
        "username": {
            "type": "string",
            "description": "用户名"
        }
    },
    "required": ["username"]
}

GET_PLAN_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "用户名"
        }
    },
    "required": ["username"]
}

COMPLETE_TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "integer",
            "description": "要标记完成的任务ID"
        },
        "username": {
            "type": "string",
            "description": "用户名"
        }
    },
    "required": ["task_id", "username"]
}

# ── Tool handlers ─────────────────────────────────────────────────

async def _generate_rehab_plan(username: str, surgery_type: str = "") -> str:
    result = rehab_plan_service.async_generate_plan(username, surgery_type)
    if result.get("success"):
        phases = result.get("phases", [])
        total = result.get("total_tasks", 0)
        notes = result.get("notes", "")
        surgery_info = f"手术类型：{surgery_type}\n" if surgery_type else ""
        return (
            f"已成功生成「{result.get('plan_title', '康复计划')}」\n"
            f"{surgery_info}"
            f"当前阶段：{result.get('current_phase', '急性期')}\n"
            f"阶段划分：{' → '.join(phases)}\n"
            f"总任务数：{total}\n"
            f"注意事项：{notes}"
        )
    return f"康复计划生成失败：{result.get('error', '未知错误')}，请稍后重试。"


async def _get_plan_status(username: str) -> str:
    plans = rehab_plan_service.get_user_plans(username)
    if not plans:
        return "当前没有康复计划。您可以告诉我想制定什么手术的康复计划，我来帮您生成。"

    lines = [f"共 {len(plans)} 个康复计划："]
    for p in plans:
        status_map = {"active": "进行中", "completed": "已完成", "cancelled": "已取消"}
        status_text = status_map.get(p.get("status"), p.get("status"))
        lines.append(
            f"  [{p.get('id')}] {p.get('plan_title', '康复计划')} — "
            f"手术：{p.get('surgery_type', '未知')}，"
            f"阶段：{p.get('current_phase', '急性期')}，"
            f"状态：{status_text}"
        )

    # 今日任务
    today_tasks = rehab_plan_service.get_today_tasks(username)
    if today_tasks:
        lines.append(f"\n今日任务（{len(today_tasks)}项）：")
        for t in today_tasks:
            status_icon = "✅" if t.get("status") == "completed" else "⬜"
            lines.append(f"  {status_icon} [{t.get('id')}] {t.get('task_content', '')}")
    else:
        lines.append("\n今日暂无康复任务。")

    return "\n".join(lines)


async def _complete_rehab_task(task_id: int, username: str) -> str:
    result = rehab_plan_service.complete_task(username, task_id)
    if result.get("success"):
        msg = f"任务 {task_id} 已标记为完成！"
        if result.get("phase_complete"):
            next_phase = result.get("next_phase")
            if next_phase:
                msg += f"\n当前阶段「{result.get('current_phase')}」的所有任务已完成，建议推进到「{next_phase}」阶段。"
            else:
                msg += f"\n所有阶段的任务已全部完成，恭喜康复！"
        return msg
    return f"任务完成标记失败：{result.get('error', '未知错误')}"


# ── Register tools ────────────────────────────────────────────────

generate_rehab_plan_tool = Tool(
    name="generate_rehab_plan",
    description="生成个性化健康管理/康复计划。当用户要求制定康复计划、生成恢复方案、健康管理规划时使用。术后患者和非术后患者均可使用。",
    parameters=GENERATE_REHAB_PLAN_SCHEMA,
    handler=_generate_rehab_plan
)

get_rehab_plan_status_tool = Tool(
    name="get_rehab_plan_status",
    description="查看康复计划状态和今日任务。当用户询问康复进度、今日任务、计划详情时使用。",
    parameters=GET_PLAN_STATUS_SCHEMA,
    handler=_get_plan_status
)

complete_rehab_task_tool = Tool(
    name="complete_rehab_task",
    description="标记康复任务为已完成。当用户说完成了一个康复任务、打卡了某项任务时使用。",
    parameters=COMPLETE_TASK_SCHEMA,
    handler=_complete_rehab_task
)

# ── 推荐运动 ──────────────────────────────────────────────────────

RECOMMEND_EXERCISES_SCHEMA = {
    "type": "object",
    "properties": {
        "surgery_type": {
            "type": "string",
            "description": "手术类型"
        },
        "current_phase": {
            "type": "string",
            "description": "当前康复阶段：急性期/恢复期/巩固期"
        }
    },
    "required": ["surgery_type", "current_phase"]
}


async def _recommend_exercises(surgery_type: str, current_phase: str) -> str:
    result = rehab_exercise_service.get_recommended(surgery_type, current_phase)
    exercises = result.get("exercises", [])
    if not exercises:
        return f"未找到适合「{current_phase}」阶段、「{surgery_type}」的运动指导。"
    lines = [f"为「{current_phase}」阶段的{surgery_type}患者推荐以下运动："]
    for i, ex in enumerate(exercises, 1):
        diff_map = {"easy": "简单", "medium": "中等", "hard": "困难"}
        cat_map = {"stretching": "拉伸", "strength": "力量", "balance": "平衡",
                   "mobility": "活动度", "breathing": "呼吸", "other": "其他"}
        lines.append(
            f"\n{i}. **{ex['title']}** ({cat_map.get(ex.get('category',''), '其他')} · "
            f"{diff_map.get(ex.get('difficulty',''), '简单')})\n"
            f"   {ex.get('description','')[:100]}\n"
            f"   时长：{ex.get('duration_minutes',5)}分钟 · 重复：{ex.get('repetitions',10)}次\n"
            f"   ⚠️ {ex.get('precautions','请遵医嘱')}"
        )
    return "\n".join(lines)


# ── 查看指标 ──────────────────────────────────────────────────────

GET_REHAB_METRICS_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "用户名"
        },
        "plan_id": {
            "type": "integer",
            "description": "康复计划ID"
        }
    },
    "required": ["username", "plan_id"]
}


async def _get_rehab_metrics(username: str, plan_id: int) -> str:
    result = rehab_metrics_service.get_latest_metrics(plan_id)
    metrics = result.get("metrics", {})
    if not metrics:
        return "该计划暂无指标记录。建议患者每日记录疼痛评分、关节活动度等指标。"
    lines = ["最新指标快照："]
    label_map = {
        "pain_vas": "疼痛VAS", "rom_flexion": "屈曲ROM", "rom_extension": "伸直ROM",
        "muscle_strength": "肌力等级", "walking_distance": "步行距离", "weight": "体重",
        "temperature": "体温", "heart_rate": "心率", "sleep_hours": "睡眠时长"
    }
    for key, val in metrics.items():
        label = label_map.get(key, key)
        lines.append(f"  {label}: {val['value']} {val.get('unit','')}  ({val.get('date','未知日期')})")
    return "\n".join(lines)


# ── Register additional tools ──────────────────────────────────────

recommend_exercises_tool = Tool(
    name="recommend_exercises",
    description="根据手术类型和当前康复阶段推荐适合的运动指导。当用户询问康复期间应该做什么运动、如何锻炼时使用。",
    parameters=RECOMMEND_EXERCISES_SCHEMA,
    handler=_recommend_exercises
)

get_rehab_metrics_tool = Tool(
    name="get_rehab_metrics",
    description="查看患者最新康复指标数据（疼痛评分、关节活动度、肌力等）。当用户询问恢复情况、指标变化时使用。",
    parameters=GET_REHAB_METRICS_SCHEMA,
    handler=_get_rehab_metrics
)

tool_registry.register(generate_rehab_plan_tool)
tool_registry.register(get_rehab_plan_status_tool)
tool_registry.register(complete_rehab_task_tool)
tool_registry.register(recommend_exercises_tool)
tool_registry.register(get_rehab_metrics_tool)
