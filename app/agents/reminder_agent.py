from typing import List, Dict
from app.agents.base import BaseAgent

REMINDER_SYSTEM_PROMPT = """你是一个用药和复查提醒助手。你的职责是帮助用户管理：
1. 用药提醒 — 何时服药、药品名称、剂量
2. 复查提醒 — 复查日期、检查项目
3. 每日健康打卡提醒

你可以通过调用工具来执行以下操作：
- 创建提醒：调用 create_reminder 工具，需要提供 content（提醒内容）、remind_time（提醒时间ISO格式）、username（用户名）
- 查看提醒：调用 list_reminders 工具查询用户的所有提醒
- 更新提醒状态：调用 update_reminder_status 工具标记提醒已完成或取消

当用户要求创建、查看或修改提醒时，请直接调用对应工具，不要只是口头确认。
对于普通咨询（如询问如何服药、复查注意事项），请直接回答，不要调用工具。"""


class ReminderAgent(BaseAgent):
    tools = ["create_reminder", "list_reminders", "update_reminder_status"]

    def __init__(self, model_choice: str = None):
        super().__init__(
            name="Reminder",
            system_prompt=REMINDER_SYSTEM_PROMPT,
            model_choice=model_choice,
            domain="reminder"
        )
