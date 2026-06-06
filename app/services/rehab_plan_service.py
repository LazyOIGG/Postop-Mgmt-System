import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.db.session import db_instance
from app.services.llm_service import llm_service, LLMServiceError


SYSTEM_PROMPT = """你是一名专业的健康管理与康复专家。请根据患者的健康档案和具体情况，生成一份分阶段健康管理和康复计划。
如果患者有手术类型，则生成术后康复计划；如果没有，则根据其健康阶段和病史生成通用的健康管理计划。
输出格式为严格的 JSON，不要输出任何其他内容，不要使用 markdown 代码块包裹。"""

FALLBACK_PLAN = {
    "plan_title": "健康管理计划",
    "phases": [
        {
            "phase": "急性期",
            "duration_days": 14,
            "daily_tasks": [
                {
                    "day": d,
                    "tasks": [
                        {"type": "medication", "content": "按时服用医生开具的药物", "reminder_time": "08:00:00"},
                        {"type": "exercise", "content": "床上简单肢体活动，预防血栓", "reminder_time": "10:00:00"},
                        {"type": "diet", "content": "清淡流质饮食，少量多餐", "reminder_time": "07:30:00"},
                    ]
                } for d in range(1, 15)
            ]
        },
        {
            "phase": "恢复期",
            "duration_days": 30,
            "daily_tasks": [
                {
                    "day": d,
                    "tasks": [
                        {"type": "medication", "content": "遵医嘱调整用药剂量", "reminder_time": "08:00:00"},
                        {"type": "exercise", "content": "适度下床活动，逐步增加运动量", "reminder_time": "10:00:00"},
                        {"type": "diet", "content": "均衡营养饮食，补充蛋白质", "reminder_time": "07:30:00"},
                        {"type": "review", "content": "定期复查伤口愈合情况", "reminder_time": "09:00:00"} if d % 7 == 0 else
                        {"type": "other", "content": "记录每日恢复状况", "reminder_time": "20:00:00"},
                    ]
                } for d in range(1, 31)
            ]
        },
        {
            "phase": "巩固期",
            "duration_days": 30,
            "daily_tasks": [
                {
                    "day": d,
                    "tasks": [
                        {"type": "exercise", "content": "规律有氧运动，增强体质", "reminder_time": "09:00:00"},
                        {"type": "diet", "content": "维持健康饮食习惯", "reminder_time": "07:30:00"},
                        {"type": "review", "content": "定期复查，评估康复进展", "reminder_time": "09:00:00"} if d % 14 == 0 else
                        {"type": "other", "content": "保持良好作息和心态", "reminder_time": "21:00:00"},
                    ]
                } for d in range(1, 31)
            ]
        }
    ],
    "notes": "请严格遵医嘱执行，如有异常请立即联系医生。"
}


def _build_generation_prompt(surgery_type: str, profile: Optional[Dict]) -> List[Dict]:
    age = profile.get("age", "未知") if profile else "未知"
    gender = profile.get("gender", "未知") if profile else "未知"
    medical_history = profile.get("medical_history", "无") if profile else "无"
    allergy_history = profile.get("allergy_history", "无") if profile else "无"
    current_medications = profile.get("current_medications", "无") if profile else "无"
    health_stage = profile.get("health_stage", "长期管理") if profile else "长期管理"

    surgery_line = f"手术类型: {surgery_type}" if surgery_type else "手术类型: 无（非术后患者，制定通用健康管理计划）"
    title_example = f"{surgery_type}术后康复计划" if surgery_type else "个性化健康管理计划"

    user_content = f"""请为以下患者生成健康管理和康复计划：

{surgery_line}
年龄: {age}
性别: {gender}
病史: {medical_history}
过敏史: {allergy_history}
当前用药: {current_medications}
健康阶段: {health_stage}

要求：
1. 分三个阶段：急性期、恢复期、巩固期
2. 每个阶段包含若干天的每日任务
3. 每日任务分为四类：用药(medication)、康复锻炼(exercise)、饮食(diet)、复查检查(review)，也可以有其他(other)
4. 急性期一般7-14天，恢复期14-30天，巩固期30-60天
5. 请根据患者具体情况（手术类型、年龄、病史等）个性化调整任务内容
6. 每个任务建议一个 reminder_time（HH:MM:SS格式）

请严格按照以下 JSON 格式输出，不要输出其他内容：
{{
  "plan_title": "{title_example}",
  "phases": [
    {{
      "phase": "急性期",
      "duration_days": 14,
      "daily_tasks": [
        {{
          "day": 1,
          "tasks": [
            {{"type": "medication", "content": "具体用药指导", "reminder_time": "08:00:00"}},
            {{"type": "exercise", "content": "具体锻炼内容", "reminder_time": "10:00:00"}},
            {{"type": "diet", "content": "具体饮食建议", "reminder_time": "07:30:00"}},
            {{"type": "review", "content": "复查安排", "reminder_time": "09:00:00"}}
          ]
        }}
      ]
    }}
  ],
  "notes": "整体注意事项..."
}}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]


def _parse_plan_json(text: str) -> Optional[Dict]:
    """尝试从 LLM 返回中解析 JSON，支持多种容错情况。"""
    text = text.strip()
    # 去掉 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首行 ```json 和末行 ```
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None


# 映射 LLM 可能返回的阶段名到数据库 ENUM 值
_PHASE_ALIASES = {
    "基础调整期": "急性期",
    "适应期": "急性期",
    "初期": "急性期",
    "习惯养成期": "恢复期",
    "恢复期": "恢复期",
    "巩固提升期": "巩固期",
    "巩固期": "巩固期",
    "维持期": "巩固期",
}


def _normalize_phase(phase_name: str) -> str:
    """将 LLM 返回的阶段名映射到数据库允许的 ENUM 值。"""
    if phase_name in ("急性期", "恢复期", "巩固期"):
        return phase_name
    return _PHASE_ALIASES.get(phase_name, "急性期")


class RehabPlanService:

    def async_generate_plan(self, username: str, surgery_type: str, plan_title: str = "") -> Dict:
        """同步版本：生成康复计划。用在 Agent tool 中。"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.generate_plan(username, surgery_type, plan_title))
        finally:
            loop.close()

    async def generate_plan(self, username: str, surgery_type: str, plan_title: str = "") -> Dict:
        """AI 生成康复计划并存储。"""
        # 1. 获取患者档案
        profile = db_instance.get_patient_profile(username)

        # 2. 构造 prompt，调用 LLM
        messages = _build_generation_prompt(surgery_type, profile)
        plan_data = None

        try:
            response = await llm_service.generate_completion_with_messages(messages)
            plan_data = _parse_plan_json(response)
        except LLMServiceError:
            pass

        # 解析失败则重试一次
        if plan_data is None:
            try:
                retry_messages = messages + [
                    {"role": "assistant", "content": response if 'response' in dir() else ""},
                    {"role": "user", "content": "请只输出合法的 JSON 对象，不要任何解释或标记。"}
                ]
                response2 = await llm_service.generate_completion_with_messages(retry_messages)
                plan_data = _parse_plan_json(response2)
            except (LLMServiceError, Exception):
                pass

        # 兜底方案
        if plan_data is None:
            plan_data = json.loads(json.dumps(FALLBACK_PLAN))
            if not plan_title:
                plan_title = f"{surgery_type}康复计划" if surgery_type else "健康管理计划"
            plan_data["plan_title"] = plan_title
        elif not plan_title and plan_data.get("plan_title"):
            plan_title = plan_data["plan_title"]

        if not plan_title:
            plan_title = f"{surgery_type}康复计划" if surgery_type else "健康管理计划"

        # 3. 存储计划
        generated_plan_text = json.dumps(plan_data, ensure_ascii=False, indent=2)
        plan_id = db_instance.save_rehab_plan(username, surgery_type, plan_title, generated_plan_text)
        if plan_id is None:
            return {"success": False, "error": "保存康复计划失败"}

        # 4. 存储每日任务 + 创建提醒
        start_date = datetime.now()
        all_tasks = []
        phases = plan_data.get("phases", [])

        for phase_info in phases:
            phase_name = _normalize_phase(phase_info.get("phase", "急性期"))
            daily_tasks = phase_info.get("daily_tasks", [])

            for day_info in daily_tasks:
                day_num = day_info.get("day", 1)
                task_date = (start_date + timedelta(days=day_num - 1)).strftime("%Y-%m-%d")

                for task in day_info.get("tasks", []):
                    task_type = task.get("type", "other")
                    task_content = task.get("content", "")
                    reminder_time = task.get("reminder_time")

                    # 创建提醒
                    reminder_id = None
                    if reminder_time:
                        reminder_id = db_instance.save_reminder(
                            username=username,
                            reminder_type="康复任务",
                            title=f"[{phase_name}] {task_content[:30]}",
                            description=task_content,
                            reminder_date=task_date,
                            reminder_time=reminder_time
                        )

                    db_instance.save_rehab_plan_task(
                        plan_id=plan_id,
                        username=username,
                        phase=phase_name,
                        task_day=day_num,
                        task_date=task_date,
                        task_type=task_type,
                        task_content=task_content,
                        reminder_id=reminder_id
                    )

                    all_tasks.append({
                        "phase": phase_name,
                        "task_day": day_num,
                        "task_date": task_date,
                        "task_type": task_type,
                        "task_content": task_content,
                        "reminder_id": reminder_id,
                        "status": "pending"
                    })

        return {
            "success": True,
            "plan_id": plan_id,
            "plan_title": plan_title,
            "surgery_type": surgery_type,
            "current_phase": "急性期",
            "phases": [p.get("phase") for p in phases],
            "total_tasks": len(all_tasks),
            "notes": plan_data.get("notes", ""),
            "generated_plan": plan_data
        }

    def get_user_plans(self, username: str, status: str = None) -> List[Dict]:
        return db_instance.get_rehab_plans(username, status)

    def get_plan_detail(self, plan_id: int) -> Optional[Dict]:
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return None
        tasks = db_instance.get_rehab_plan_tasks(plan_id)
        # 按阶段分组
        phases = {}
        for t in tasks:
            phase = t.get("phase", "急性期")
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(t)
        plan["phases"] = phases
        return plan

    def get_today_tasks(self, username: str) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return db_instance.get_today_rehab_tasks(username, today)

    def complete_task(self, username: str, task_id: int) -> Dict:
        task = db_instance.get_rehab_plan_task(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}
        if task.get("username") != username:
            return {"success": False, "error": "无权操作此任务"}

        ok = db_instance.update_rehab_task_status(task_id, "completed")
        if not ok:
            return {"success": False, "error": "更新任务状态失败"}

        # 同步提醒状态
        reminder_id = task.get("reminder_id")
        if reminder_id:
            db_instance.update_reminder_status(username, reminder_id, "completed")

        # 检查当前阶段是否全部完成
        plan = db_instance.get_rehab_plan(task["plan_id"])
        current_phase = plan.get("current_phase", "急性期") if plan else "急性期"
        stats = db_instance.get_rehab_plan_phase_task_stats(task["plan_id"], current_phase)
        phase_complete = stats.get("total", 0) > 0 and stats.get("total") == stats.get("completed")

        # 推荐下一个阶段
        phase_order = ["急性期", "恢复期", "巩固期"]
        next_phase = None
        if phase_complete and current_phase in phase_order:
            idx = phase_order.index(current_phase)
            if idx < len(phase_order) - 1:
                next_phase = phase_order[idx + 1]

        # 更新计划统计（完成率、连续打卡）
        db_instance.update_rehab_plan_stats(task["plan_id"])

        # 检查并触发成就
        from app.services.rehab_achievement_service import rehab_achievement_service
        ach_result = rehab_achievement_service.check_and_award(username, task["plan_id"])
        new_achievements = ach_result.get("new_achievements", [])

        return {
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "phase_complete": phase_complete,
            "current_phase": current_phase,
            "next_phase": next_phase,
            "phase_stats": stats,
            "new_achievements": new_achievements
        }

    def cancel_plan(self, plan_id: int, username: str) -> bool:
        tasks = db_instance.get_rehab_plan_tasks(plan_id)
        for t in tasks:
            reminder_id = t.get("reminder_id")
            if reminder_id:
                db_instance.update_reminder_status(username, reminder_id, "cancelled")
        return db_instance.update_rehab_plan_status(plan_id, "cancelled")

    def advance_phase(self, plan_id: int, new_phase: str) -> bool:
        phase_order = ["急性期", "恢复期", "巩固期"]
        if new_phase not in phase_order:
            return False
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return False
        current = plan.get("current_phase", "急性期")
        if current in phase_order and new_phase in phase_order:
            if phase_order.index(new_phase) < phase_order.index(current):
                return False  # 不能回退
        return db_instance.update_rehab_plan_phase(plan_id, new_phase)

    def get_dashboard_data(self, plan_id: int) -> Dict:
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return {"success": False, "error": "计划不存在"}

        stats = db_instance.get_rehab_dashboard_stats(plan_id)
        today = __import__("datetime").datetime.now()
        year, month = today.year, today.month

        calendar_data = db_instance.get_rehab_calendar_data(plan_id, year, month)
        today_tasks = db_instance.get_today_rehab_tasks(
            plan.get("username"), today.strftime("%Y-%m-%d"))
        latest_metrics = db_instance.get_latest_metrics(plan_id)

        # 阶段统计
        phase_order = ["急性期", "恢复期", "巩固期"]
        phase_stats = {}
        for p in phase_order:
            stats_p = db_instance.get_rehab_plan_phase_task_stats(plan_id, p)
            phase_stats[p] = stats_p

        return {
            "success": True,
            "plan": plan,
            "stats": stats,
            "calendar": calendar_data,
            "today_tasks": today_tasks,
            "latest_metrics": latest_metrics,
            "phase_stats": phase_stats
        }

    def get_calendar_data(self, plan_id: int, year: int, month: int) -> Dict:
        data = db_instance.get_rehab_calendar_data(plan_id, year, month)
        return {"success": True, "calendar": data}


rehab_plan_service = RehabPlanService()
