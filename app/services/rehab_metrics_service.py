from typing import Dict, List, Optional
from app.db.session import db_instance


class RehabMetricsService:

    def save_metric(self, username: str, plan_id: int, data: dict) -> Dict:
        metric_id = db_instance.save_rehab_metric(
            plan_id=plan_id,
            username=username,
            metric_date=data["metric_date"],
            metric_type=data["metric_type"],
            metric_value=data["metric_value"],
            metric_unit=data.get("metric_unit", ""),
            note=data.get("note", "")
        )
        if metric_id is None:
            return {"success": False, "error": "保存指标失败"}
        return {"success": True, "metric_id": metric_id}

    def get_metrics(
        self, plan_id: int, metric_type: str = None,
        date_from: str = None, date_to: str = None
    ) -> Dict:
        data = db_instance.get_rehab_metrics(
            plan_id=plan_id, metric_type=metric_type,
            date_from=date_from, date_to=date_to
        )
        return {"success": True, "metrics": data}

    def get_latest_metrics(self, plan_id: int) -> Dict:
        metrics = db_instance.get_latest_metrics(plan_id)
        return {"success": True, "metrics": metrics}

    def get_trend_data(self, plan_id: int, metric_type: str,
                       date_from: str = None, date_to: str = None) -> Dict:
        """返回适合前端图表的数据格式：{dates: [...], values: [...]}"""
        raw = db_instance.get_rehab_metrics(
            plan_id=plan_id, metric_type=metric_type,
            date_from=date_from, date_to=date_to
        )
        dates = [m["metric_date"] for m in raw]
        values = [float(m["metric_value"]) for m in raw]
        return {"success": True, "dates": dates, "values": values,
                "metric_type": metric_type}


rehab_metrics_service = RehabMetricsService()
