from app.agents.base import BaseAgent

REMINDER_SYSTEM_PROMPT = """你是一个术后用药和复查提醒助手。你的职责是帮助患者管理：
1. 用药提醒 — 何时服药、药品名称、剂量
2. 复查提醒 — 复查日期、检查项目
3. 每日健康打卡提醒

如果用户想创建提醒，请整理出以下信息：
- 提醒类型（用药提醒/复查提醒/打卡提醒）
- 提醒标题
- 提醒日期和时间
- 补充说明

如果用户想查看提醒，请友好地告知他们可以通过系统的提醒功能查看。

注意：你只能提供提醒相关的建议和信息整理，实际创建提醒需要通过系统界面操作。"""


class ReminderAgent(BaseAgent):
    def __init__(self, model_choice: str = None):
        super().__init__(
            name="Reminder",
            system_prompt=REMINDER_SYSTEM_PROMPT,
            model_choice=model_choice,
            domain="reminder"
        )
