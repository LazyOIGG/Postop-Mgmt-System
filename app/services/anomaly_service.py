import math
import re
from typing import Dict, List, Optional

from app.db.session import db_instance


class AnomalyService:
    """时序异常检测服务 — 基于滑动窗口 + Z-score 检测体征趋势异常"""

    # Z-score 阈值：超过此值视为异常
    Z_SCORE_THRESHOLD = 2.0
    # 体温连续上升天数阈值
    CONSECUTIVE_TEMP_RISE_DAYS = 3
    # 体温均值预警线
    TEMP_MEAN_WARNING = 37.5

    def _parse_blood_pressure(self, bp: str) -> Optional[tuple]:
        """解析血压字符串 '120/80' -> (收缩压, 舒张压)"""
        if not bp:
            return None
        m = re.match(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$", bp)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None

    def _calc_z_scores(self, values: List[Optional[float]]) -> List[Optional[float]]:
        """计算 Z-score 列表，跳过 None 值"""
        valid = [v for v in values if v is not None]
        if len(valid) < 3:
            return [None] * len(values)

        mean = sum(valid) / len(valid)
        variance = sum((v - mean) ** 2 for v in valid) / len(valid)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            return [None if v is None else 0.0 for v in values]

        return [None if v is None else (v - mean) / std for v in values]

    def _detect_consecutive_temp_rise(self, temperatures: List[Optional[float]], dates: List[str]) -> List[Dict]:
        """检测体温连续上升趋势"""
        anomalies = []
        # 提取连续非 None 的体温序列
        consecutive = []
        consecutive_dates = []
        for i, temp in enumerate(temperatures):
            if temp is not None:
                consecutive.append(temp)
                consecutive_dates.append(dates[i])
            else:
                # 检查已有的连续序列
                if len(consecutive) >= self.CONSECUTIVE_TEMP_RISE_DAYS:
                    rising = all(consecutive[j] < consecutive[j + 1] for j in range(len(consecutive) - 1))
                    if rising:
                        anomalies.append({
                            "metric": "temperature",
                            "description": f"体温连续 {len(consecutive)} 天上升 ({consecutive_dates[0]} ~ {consecutive_dates[-1]})",
                            "severity": "high" if consecutive[-1] >= 38.0 else "medium",
                            "values": consecutive,
                            "dates": consecutive_dates,
                        })
                consecutive = []
                consecutive_dates = []

        # 处理末尾的连续序列
        if len(consecutive) >= self.CONSECUTIVE_TEMP_RISE_DAYS:
            rising = all(consecutive[j] < consecutive[j + 1] for j in range(len(consecutive) - 1))
            if rising:
                anomalies.append({
                    "metric": "temperature",
                    "description": f"体温连续 {len(consecutive)} 天上升 ({consecutive_dates[0]} ~ {consecutive_dates[-1]})",
                    "severity": "high" if consecutive[-1] >= 38.0 else "medium",
                    "values": consecutive,
                    "dates": consecutive_dates,
                })

        return anomalies

    def detect_trend_anomaly(self, username: str, days: int = 7) -> Dict:
        """分析近 N 天打卡数据，检测体征趋势异常

        Returns:
            {
                "has_anomaly": bool,
                "anomalies": [
                    {"metric": str, "description": str, "severity": str, ...}
                ]
            }
        """
        checkins = db_instance.get_daily_checkins(username, limit=days)
        if not checkins or len(checkins) < 3:
            return {"has_anomaly": False, "anomalies": []}

        # 按时间正序排列
        checkins = sorted(checkins, key=lambda x: x.get("checkin_date", ""))

        dates = [str(c.get("checkin_date", "")) for c in checkins]
        temperatures = [c.get("temperature") for c in checkins]
        blood_sugars = [c.get("blood_sugar") for c in checkins]
        heart_rates = [float(c["heart_rate"]) if c.get("heart_rate") is not None else None for c in checkins]

        # 收缩压列表
        systolics = []
        for c in checkins:
            bp = self._parse_blood_pressure(c.get("blood_pressure", ""))
            systolics.append(float(bp[0]) if bp else None)

        anomalies = []

        # 1. Z-score 检测各指标
        metric_configs = [
            ("temperature", temperatures, "体温"),
            ("blood_sugar", blood_sugars, "血糖"),
            ("heart_rate", heart_rates, "心率"),
            ("systolic_bp", systolics, "收缩压"),
        ]

        for metric_name, values, label in metric_configs:
            z_scores = self._calc_z_scores(values)
            for i, z in enumerate(z_scores):
                if z is not None and abs(z) > self.Z_SCORE_THRESHOLD:
                    direction = "异常偏高" if z > 0 else "异常偏低"
                    anomalies.append({
                        "metric": metric_name,
                        "description": f"{label}在 {dates[i]} {direction}（值: {values[i]}, Z-score: {z:.2f}）",
                        "severity": "high" if abs(z) > 2.5 else "medium",
                        "date": dates[i],
                        "value": values[i],
                        "z_score": round(z, 2),
                    })

        # 2. 体温连续上升检测
        temp_rise = self._detect_consecutive_temp_rise(temperatures, dates)
        anomalies.extend(temp_rise)

        # 3. 体温均值过高检测
        valid_temps = [t for t in temperatures if t is not None]
        if valid_temps:
            temp_mean = sum(valid_temps) / len(valid_temps)
            if temp_mean > self.TEMP_MEAN_WARNING:
                anomalies.append({
                    "metric": "temperature",
                    "description": f"近 {days} 天体温均值 {temp_mean:.1f}℃，高于预警线 {self.TEMP_MEAN_WARNING}℃",
                    "severity": "high" if temp_mean >= 38.0 else "medium",
                    "mean_value": round(temp_mean, 1),
                })

        # 去重：同一 metric+date 只保留 severity 最高的
        seen = {}
        for a in anomalies:
            key = f"{a['metric']}:{a.get('date', 'overall')}"
            if key not in seen or (a["severity"] == "high" and seen[key]["severity"] != "high"):
                seen[key] = a
        anomalies = list(seen.values())

        return {
            "has_anomaly": len(anomalies) > 0,
            "anomalies": anomalies,
        }

    def check_consecutive_abnormal(self, username: str, days: int = 3) -> bool:
        """检查是否连续 N 天打卡异常"""
        checkins = db_instance.get_daily_checkins(username, limit=days)
        if not checkins or len(checkins) < days:
            return False

        # 按时间正序
        checkins = sorted(checkins, key=lambda x: x.get("checkin_date", ""))
        # 取最近 N 天
        recent = checkins[-days:]
        return all(c.get("abnormal_flag") == 1 for c in recent)

    def run_full_check(self, username: str) -> Dict:
        """综合异常检测，返回完整预警结果

        Returns:
            {
                "has_alert": bool,
                "consecutive_abnormal": bool,
                "trend_anomaly": {"has_anomaly": bool, "anomalies": [...]},
                "alert_summary": str  # 给 LLM 的文字摘要
            }
        """
        trend = self.detect_trend_anomaly(username, days=7)
        consecutive = self.check_consecutive_abnormal(username, days=3)

        has_alert = trend["has_anomaly"] or consecutive

        summary_parts = []
        if consecutive:
            summary_parts.append("患者连续 3 天打卡异常，需要密切关注")
        for a in trend.get("anomalies", []):
            summary_parts.append(a["description"])

        return {
            "has_alert": has_alert,
            "consecutive_abnormal": consecutive,
            "trend_anomaly": trend,
            "alert_summary": "；".join(summary_parts) if summary_parts else "",
        }


anomaly_service = AnomalyService()
