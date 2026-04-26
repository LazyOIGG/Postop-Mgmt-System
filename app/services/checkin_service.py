from typing import Dict, List, Tuple
import re


class CheckinService:
    def analyze_checkin(self, data: Dict) -> Dict:
        reasons: List[str] = []
        abnormal_flag = 0

        temperature = data.get("temperature")
        blood_pressure = data.get("blood_pressure", "")
        blood_sugar = data.get("blood_sugar")
        heart_rate = data.get("heart_rate")
        symptoms = data.get("symptoms", "") or ""

        if temperature is not None:
            if temperature >= 39.0:
                abnormal_flag = 1
                reasons.append(f"体温较高（{temperature}℃）")
            elif temperature >= 37.8:
                abnormal_flag = 1
                reasons.append(f"体温偏高（{temperature}℃）")

        if blood_pressure:
            m = re.match(r"^\s*(\d{2,3})/(\d{2,3})\s*$", blood_pressure)
            if m:
                systolic = int(m.group(1))
                diastolic = int(m.group(2))
                if systolic >= 180 or diastolic >= 120:
                    abnormal_flag = 1
                    reasons.append(f"血压严重异常（{systolic}/{diastolic}）")
                elif systolic >= 140 or diastolic >= 90:
                    abnormal_flag = 1
                    reasons.append(f"血压偏高（{systolic}/{diastolic}）")

        if blood_sugar is not None:
            if blood_sugar >= 11.1:
                abnormal_flag = 1
                reasons.append(f"血糖较高（{blood_sugar} mmol/L）")

        if heart_rate is not None:
            if heart_rate > 120 or heart_rate < 50:
                abnormal_flag = 1
                reasons.append(f"心率异常（{heart_rate} 次/分）")

        high_risk_words = ["胸痛", "呼吸困难", "意识不清", "抽搐", "持续呕吐", "大量出血"]
        for word in high_risk_words:
            if word in symptoms:
                abnormal_flag = 1
                reasons.append(f"症状中包含高风险描述：{word}")

        if not reasons:
            reasons.append("今日打卡未发现明显异常")

        return {
            "abnormal_flag": abnormal_flag,
            "abnormal_reason": "；".join(reasons)
        }


checkin_service = CheckinService()