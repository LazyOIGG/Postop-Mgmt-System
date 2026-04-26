from typing import Dict, List
from app.db.session import db_instance


class OverviewService:
    def build_dashboard(self, username: str, days: int = 7) -> Dict:
        profile = db_instance.get_patient_profile(username)
        latest_assessment = db_instance.get_latest_health_assessment(username)
        recent_checkins = db_instance.get_recent_checkins_for_overview(username, days=days)
        summary = db_instance.get_checkin_summary_stats(username, days=days)
        reminder_stats = db_instance.get_today_reminder_stats(username)

        trend = {
            "dates": [],
            "temperature": [],
            "blood_sugar": [],
            "heart_rate": [],
            "abnormal_flags": []
        }

        abnormal_records = []

        for item in recent_checkins:
            trend["dates"].append(str(item.get("checkin_date", "")))
            trend["temperature"].append(item.get("temperature"))
            trend["blood_sugar"].append(item.get("blood_sugar"))
            trend["heart_rate"].append(item.get("heart_rate"))
            trend["abnormal_flags"].append(item.get("abnormal_flag", 0))

            if item.get("abnormal_flag"):
                abnormal_records.append({
                    "date": str(item.get("checkin_date", "")),
                    "reason": item.get("abnormal_reason", ""),
                    "symptoms": item.get("symptoms", "")
                })

        overview_cards = {
            "real_name": profile.get("real_name", "") if profile else "",
            "gender": profile.get("gender", "") if profile else "",
            "age": profile.get("age", None) if profile else None,
            "health_stage": profile.get("health_stage", "") if profile else "",
            "latest_risk_level": latest_assessment.get("risk_level", "") if latest_assessment else "",
            "latest_assessment_time": str(latest_assessment.get("created_at", "")) if latest_assessment else "",
            "total_checkins": int(summary.get("total_checkins", 0) or 0) if summary else 0,
            "abnormal_count": int(summary.get("abnormal_count", 0) or 0) if summary else 0,
            "avg_temperature": round(float(summary["avg_temperature"]), 2) if summary and summary.get("avg_temperature") is not None else None,
            "avg_heart_rate": round(float(summary["avg_heart_rate"]), 2) if summary and summary.get("avg_heart_rate") is not None else None,
            "avg_blood_sugar": round(float(summary["avg_blood_sugar"]), 2) if summary and summary.get("avg_blood_sugar") is not None else None,
            "today_pending_reminders": reminder_stats.get("pending_count", 0),
            "today_completed_reminders": reminder_stats.get("completed_count", 0)
        }

        return {
            "overview": overview_cards,
            "trend": trend,
            "abnormal_records": abnormal_records,
            "latest_assessment": latest_assessment,
            "profile": profile
        }


overview_service = OverviewService()