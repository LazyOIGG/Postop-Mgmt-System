from typing import Dict, List
from app.db.session import db_instance


class ReminderService:
    def get_all_reminders(self, username: str):
        return db_instance.get_reminders(username)

    def get_today_stats(self, username: str):
        return db_instance.get_today_reminder_stats(username)

    def create_default_checkin_reminder(self, username: str, reminder_date: str):
        return db_instance.save_reminder(
            username=username,
            reminder_type="打卡提醒",
            title="每日健康打卡",
            description="请记得完成今日健康打卡",
            reminder_date=reminder_date,
            reminder_time="20:00:00"
        )


reminder_service = ReminderService()