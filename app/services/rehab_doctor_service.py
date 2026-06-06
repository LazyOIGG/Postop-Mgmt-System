from typing import Dict, List
from app.db.session import db_instance


class RehabDoctorService:

    def get_patient_rehab_overview(self, username: str) -> Dict:
        """获取患者的康复全貌数据"""
        plans = db_instance.get_rehab_plans(username, status="active")
        if not plans:
            return {"success": False, "error": "该患者无活跃的康复计划"}

        plan = plans[0]
        plan_id = plan["id"]

        # 仪表盘统计
        stats = db_instance.get_rehab_dashboard_stats(plan_id)
        latest_metrics = db_instance.get_latest_metrics(plan_id)

        # 阶段统计
        phase_order = ["急性期", "恢复期", "巩固期"]
        phase_stats = {}
        for p in phase_order:
            s = db_instance.get_rehab_plan_phase_task_stats(plan_id, p)
            phase_stats[p] = s

        # 近期日志
        journals = db_instance.get_rehab_journals(plan_id)

        # 成就
        achievements = db_instance.get_user_achievements(username, plan_id)

        return {
            "success": True,
            "plan": plan,
            "stats": stats,
            "phase_stats": phase_stats,
            "latest_metrics": latest_metrics,
            "journals": journals[:10],
            "achievement_count": len(achievements)
        }

    def get_patient_metrics(
        self, username: str, metric_type: str = None,
        date_from: str = None, date_to: str = None
    ) -> Dict:
        """医生查看患者指标趋势"""
        plans = db_instance.get_rehab_plans(username, status="active")
        if not plans:
            return {"success": False, "error": "该患者无活跃的康复计划"}

        plan_id = plans[0]["id"]
        metrics = db_instance.get_rehab_metrics(
            plan_id=plan_id, metric_type=metric_type,
            date_from=date_from, date_to=date_to
        )
        return {"success": True, "metrics": metrics}

    def send_feedback(self, doctor_username: str, patient_username: str,
                      plan_id: int, feedback_content: str) -> Dict:
        """医生给患者发送康复反馈（追加到 doctor_feedback JSON 字段）"""
        import json
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan or plan.get("username") != patient_username:
            return {"success": False, "error": "计划不存在或不匹配患者"}

        existing = plan.get("doctor_feedback")
        if isinstance(existing, str):
            existing = json.loads(existing) if existing else []
        elif existing is None:
            existing = []

        from datetime import datetime
        existing.append({
            "doctor": doctor_username,
            "content": feedback_content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        cursor = db_instance.connection.cursor()
        cursor.execute(
            "UPDATE rehab_plans SET doctor_feedback = %s WHERE id = %s",
            (json.dumps(existing, ensure_ascii=False), plan_id)
        )
        db_instance.connection.commit()
        cursor.close()

        return {"success": True, "message": "反馈已发送"}


rehab_doctor_service = RehabDoctorService()
