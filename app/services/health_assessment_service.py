from typing import Dict, List
import re
from app.services.llm_service import llm_service


class HealthAssessmentService:
    def __init__(self):
        self.high_risk_keywords = [
            "呼吸困难", "胸痛", "意识不清", "抽搐", "持续高烧",
            "高热", "严重出血", "呕血", "黑便", "昏迷",
            "伤口裂开", "大量渗液", "化脓", "严重感染"
        ]

        self.medium_risk_keywords = [
            "发热", "头晕", "恶心", "呕吐", "疼痛加重",
            "红肿", "渗液", "食欲差", "失眠", "心慌",
            "血压偏高", "血糖偏高", "腹泻", "便秘"
        ]

        self.low_risk_keywords = [
            "恢复良好", "轻微疼痛", "无发热", "能正常饮食",
            "按时服药", "正常活动", "情况稳定", "食欲正常"
        ]

    def _match_keywords(self, text: str, keywords: List[str]) -> List[str]:
        return [kw for kw in keywords if kw in text]

    def _detect_temperature(self, text: str):
        m = re.search(r"(体温|温度)[:：]?\s*(\d+(?:\.\d+)?)", text)
        if m:
            return float(m.group(2))
        return None

    def _detect_blood_pressure(self, text: str):
        m = re.search(r"(血压)[:：]?\s*(\d{2,3})/(\d{2,3})", text)
        if m:
            return int(m.group(2)), int(m.group(3))
        return None

    def rule_based_assess(self, text: str) -> Dict:
        text = text.strip()
        reasons = []
        need_hospital = False

        high_hits = self._match_keywords(text, self.high_risk_keywords)
        medium_hits = self._match_keywords(text, self.medium_risk_keywords)
        low_hits = self._match_keywords(text, self.low_risk_keywords)

        risk_level = "低风险"

        temp = self._detect_temperature(text)
        if temp is not None:
            if temp >= 39.0:
                risk_level = "高风险"
                reasons.append(f"体温较高（{temp}℃）")
                need_hospital = True
            elif temp >= 37.8:
                risk_level = "中风险"
                reasons.append(f"体温升高（{temp}℃）")

        bp = self._detect_blood_pressure(text)
        if bp:
            systolic, diastolic = bp
            if systolic >= 180 or diastolic >= 120:
                risk_level = "高风险"
                reasons.append(f"血压严重异常（{systolic}/{diastolic}）")
                need_hospital = True
            elif systolic >= 140 or diastolic >= 90:
                if risk_level != "高风险":
                    risk_level = "中风险"
                reasons.append(f"血压偏高（{systolic}/{diastolic}）")

        if high_hits:
            risk_level = "高风险"
            reasons.extend([f"检测到高风险关键词：{x}" for x in high_hits])
            need_hospital = True
        elif medium_hits and risk_level != "高风险":
            risk_level = "中风险"
            reasons.extend([f"检测到中风险关键词：{x}" for x in medium_hits])
        elif low_hits and risk_level == "低风险":
            reasons.extend([f"检测到恢复/稳定描述：{x}" for x in low_hits])

        if not reasons:
            reasons.append("当前未发现明显高危信号，建议继续观察并保持健康记录")

        return {
            "risk_level": risk_level,
            "risk_reasons": reasons,
            "need_hospital": need_hospital
        }

    async def generate_health_advice(self, text: str, risk_result: Dict) -> str:
        prompt = f"""
你是医院患者全周期健康管理系统中的健康评估助手。
请根据以下患者输入，给出简洁、易懂、实用的健康建议。

患者输入：
{text}

系统规则评估结果：
- 风险等级：{risk_result["risk_level"]}
- 风险原因：{', '.join(risk_result["risk_reasons"])}
- 是否建议尽快线下就医：{"是" if risk_result["need_hospital"] else "否"}

请输出：
1. 当前情况总结
2. 建议措施（3-5条）
3. 是否建议线下就医
4. 需要重点观察的内容

要求：
- 语言通俗
- 不要过度诊断
- 高风险时明确建议尽快就医
"""
        return await llm_service.generate_completion(prompt)

    async def assess(self, text: str, source_type: str = "text") -> Dict:
        risk_result = self.rule_based_assess(text)
        advice = await self.generate_health_advice(text, risk_result)

        return {
            "source_type": source_type,
            "input_text": text,
            "risk_level": risk_result["risk_level"],
            "risk_reasons": risk_result["risk_reasons"],
            "need_hospital": risk_result["need_hospital"],
            "advice": advice
        }


health_assessment_service = HealthAssessmentService()