from app.db.session import db_instance


class DashboardService:
    def get_system_dashboard(self):
        basic_stats = db_instance.get_system_basic_stats()
        ratio_stats = db_instance.get_system_ratio_stats()
        recent_high_risk = db_instance.get_recent_high_risk_records(limit=10)
        recent_abnormal_checkins = db_instance.get_recent_abnormal_checkins(limit=10)

        return {
            "basic_stats": basic_stats,
            "ratio_stats": ratio_stats,
            "recent_high_risk": recent_high_risk,
            "recent_abnormal_checkins": recent_abnormal_checkins
        }


dashboard_service = DashboardService()
