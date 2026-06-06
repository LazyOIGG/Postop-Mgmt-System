import json
from typing import Dict, List
from datetime import datetime
from app.db.session import db_instance


class RehabAchievementService:

    def get_all_defs(self) -> Dict:
        defs = db_instance.get_all_achievement_defs()
        return {"success": True, "achievements": defs}

    def get_user_achievements(self, username: str, plan_id: int) -> Dict:
        achievements = db_instance.get_user_achievements(username, plan_id)
        return {"success": True, "achievements": achievements}

    def check_and_award(self, username: str, plan_id: int) -> Dict:
        """检查所有成就条件，授予新成就，返回新获得的成就列表"""
        all_defs = db_instance.get_all_achievement_defs()
        existing = db_instance.get_user_achievements(username, plan_id)
        existing_codes = {a["code"] for a in existing}

        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return {"success": True, "new_achievements": []}

        new_achievements = []

        for ach in all_defs:
            if ach["code"] in existing_codes:
                continue
            condition = ach.get("condition_json", {})
            if isinstance(condition, str):
                condition = json.loads(condition)

            if self._check_condition(username, plan_id, condition):
                awarded = db_instance.award_achievement(username, plan_id, ach["id"])
                if awarded:
                    new_achievements.append({
                        "code": ach["code"], "name": ach["name"],
                        "description": ach["description"], "points": ach["points"],
                        "category": ach["category"]
                    })

        return {"success": True, "new_achievements": new_achievements}

    def _check_condition(self, username: str, plan_id: int, condition: dict) -> bool:
        cond_type = condition.get("type", "")

        if cond_type == "streak":
            return self._check_streak(plan_id, condition["days"])
        elif cond_type == "phase_complete":
            return self._check_phase_complete(plan_id, condition["phase"])
        elif cond_type == "compliance":
            return self._check_compliance(plan_id, condition["days"])
        elif cond_type == "metric":
            return self._check_metric(plan_id, condition["target"],
                                      condition.get("operator", "lte"),
                                      condition["value"])
        elif cond_type == "metric_improvement":
            return self._check_metric_improvement(plan_id, condition["target"],
                                                  condition["delta"])
        elif cond_type == "task_complete":
            return self._check_task_keyword(plan_id, condition.get("keyword", ""))
        elif cond_type == "journal_streak":
            return self._check_journal_streak(plan_id, condition["days"])
        return False

    def _check_streak(self, plan_id: int, required_days: int) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = db_instance.connection.cursor(dictionary=True)
        query = """
            SELECT task_date, COUNT(*) as total,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as done
            FROM rehab_plan_tasks WHERE plan_id = %s AND task_date <= %s
            GROUP BY task_date ORDER BY task_date DESC LIMIT %s
        """
        cursor.execute(query, (plan_id, today, required_days))
        rows = cursor.fetchall()
        cursor.close()
        if len(rows) < required_days:
            return False
        return all(r["total"] > 0 and r["total"] == r["done"] for r in rows)

    def _check_phase_complete(self, plan_id: int, phase: str) -> bool:
        stats = db_instance.get_rehab_plan_phase_task_stats(plan_id, phase)
        return stats["total"] > 0 and stats["total"] == stats["completed"]

    def _check_compliance(self, plan_id: int, days: int) -> bool:
        cursor = db_instance.connection.cursor(dictionary=True)
        query = """
            SELECT task_date, COUNT(*) as total,
                   SUM(CASE WHEN status='completed' OR task_type != 'medication' THEN 1 ELSE 0 END) as done
            FROM rehab_plan_tasks
            WHERE plan_id = %s AND task_type = 'medication' AND task_date <= CURDATE()
            GROUP BY task_date ORDER BY task_date DESC LIMIT %s
        """
        cursor.execute(query, (plan_id, days))
        rows = cursor.fetchall()
        cursor.close()
        return len(rows) >= days and all(r["total"] == r["done"] for r in rows)

    def _check_metric(self, plan_id: int, target: str, operator: str, value: float) -> bool:
        metrics = db_instance.get_latest_metrics(plan_id)
        current = metrics.get(target, {}).get("value")
        if current is None:
            return False
        if operator == "lte":
            return float(current) <= value
        elif operator == "gte":
            return float(current) >= value
        return False

    def _check_metric_improvement(self, plan_id: int, target: str, delta: float) -> bool:
        metrics = db_instance.get_rehab_metrics(plan_id, metric_type=target)
        if len(metrics) < 2:
            return False
        first_val = float(metrics[0]["metric_value"])
        last_val = float(metrics[-1]["metric_value"])
        return (last_val - first_val) >= delta

    def _check_task_keyword(self, plan_id: int, keyword: str) -> bool:
        cursor = db_instance.connection.cursor(dictionary=True)
        query = """
            SELECT COUNT(*) as cnt FROM rehab_plan_tasks
            WHERE plan_id = %s AND status = 'completed' AND task_content LIKE %s
        """
        cursor.execute(query, (plan_id, f"%{keyword}%"))
        result = cursor.fetchone()
        cursor.close()
        return (result["cnt"] if result else 0) > 0

    def _check_journal_streak(self, plan_id: int, days: int) -> bool:
        cursor = db_instance.connection.cursor(dictionary=True)
        query = """
            SELECT journal_date FROM rehab_journals
            WHERE plan_id = %s ORDER BY journal_date DESC LIMIT %s
        """
        cursor.execute(query, (plan_id, days))
        rows = cursor.fetchall()
        cursor.close()
        if len(rows) < days:
            return False
        dates = [r["journal_date"] for r in rows]
        for i in range(len(dates) - 1):
            d1 = datetime.strptime(str(dates[i]), "%Y-%m-%d")
            d2 = datetime.strptime(str(dates[i + 1]), "%Y-%m-%d")
            if (d1 - d2).days != 1:
                return False
        return True


rehab_achievement_service = RehabAchievementService()
