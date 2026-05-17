from datetime import datetime
from app.db.session import db_instance
from .base import Tool
from .registry import tool_registry

# ── Tool schemas ──────────────────────────────────────────────────

CREATE_REMINDER_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "提醒内容，如吃药名称、复查项目"
        },
        "remind_time": {
            "type": "string",
            "description": "提醒时间，ISO格式如 2026-05-18T09:00:00"
        },
        "username": {
            "type": "string",
            "description": "用户名"
        }
    },
    "required": ["content", "remind_time", "username"]
}

LIST_REMINDERS_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "用户名"
        }
    },
    "required": ["username"]
}

UPDATE_REMINDER_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "reminder_id": {
            "type": "integer",
            "description": "提醒记录ID"
        },
        "status": {
            "type": "string",
            "enum": ["completed", "cancelled"],
            "description": "新状态: completed(已完成) 或 cancelled(已取消)"
        },
        "username": {
            "type": "string",
            "description": "用户名"
        }
    },
    "required": ["reminder_id", "status", "username"]
}

# ── Tool handlers ─────────────────────────────────────────────────

async def _create_reminder(content: str, remind_time: str, username: str) -> str:
    try:
        dt = datetime.fromisoformat(remind_time)
        reminder_date = dt.strftime("%Y-%m-%d")
        reminder_time = dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return "错误：提醒时间格式不正确，请使用 ISO 格式，如 2026-05-18T09:00:00"

    success = db_instance.save_reminder(
        username=username,
        reminder_type="用药提醒",
        title=content[:50],
        description=content,
        reminder_date=reminder_date,
        reminder_time=reminder_time
    )
    if success:
        return f"已成功创建提醒：{content}，时间：{reminder_date} {reminder_time}"
    return "提醒创建失败，请稍后重试。"


async def _list_reminders(username: str) -> str:
    reminders = db_instance.get_reminders(username)
    if not reminders:
        return "当前没有提醒记录。"
    lines = [f"共 {len(reminders)} 条提醒："]
    for r in reminders:
        rid = r.get("id", "?")
        title = r.get("title", "")
        rdate = r.get("reminder_date", "")
        rtime = r.get("reminder_time", "")
        status = r.get("status", "pending")
        lines.append(f"  [{rid}] {title} — {rdate} {rtime}（{status}）")
    return "\n".join(lines)


async def _update_reminder_status(reminder_id: int, status: str, username: str) -> str:
    if status not in ("completed", "cancelled"):
        return f"错误：无效状态 {status}，仅支持 completed 或 cancelled"
    success = db_instance.update_reminder_status(username, reminder_id, status)
    if success:
        return f"提醒 {reminder_id} 状态已更新为 {status}"
    return f"提醒 {reminder_id} 状态更新失败，请检查ID是否正确。"


# ── Register tools ────────────────────────────────────────────────

create_reminder_tool = Tool(
    name="create_reminder",
    description="创建一条用药/复查提醒。当用户要求设置提醒、吃药提醒、复查提醒时使用。",
    parameters=CREATE_REMINDER_SCHEMA,
    handler=_create_reminder
)

list_reminders_tool = Tool(
    name="list_reminders",
    description="查询用户的所有提醒记录。当用户询问有哪些提醒、查看提醒列表时使用。",
    parameters=LIST_REMINDERS_SCHEMA,
    handler=_list_reminders
)

update_reminder_status_tool = Tool(
    name="update_reminder_status",
    description="更新提醒状态为已完成或已取消。当用户说完成了某条提醒、取消提醒时使用。",
    parameters=UPDATE_REMINDER_STATUS_SCHEMA,
    handler=_update_reminder_status
)

tool_registry.register(create_reminder_tool)
tool_registry.register(list_reminders_tool)
tool_registry.register(update_reminder_status_tool)
