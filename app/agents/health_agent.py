from typing import AsyncGenerator
from app.agents.base import BaseAgent, AgentResponse
from app.services.health_assessment_service import health_assessment_service

HEALTH_AGENT_SYSTEM_PROMPT = """你是一个术后健康风险评估助手。你的职责是：
1. 分析患者描述的身体症状和不适
2. 根据风险等级（高风险/中风险/低风险）给出对应的健康建议
3. 判断是否需要建议患者尽快就医
4. 提供术后恢复指导

回答要求：
- 结构清晰：先总结情况，再给出建议措施
- 高风险情况必须明确建议就医
- 语言通俗易懂，避免引起不必要的恐慌
- 不要过度诊断，必要时建议咨询主治医生"""


class HealthAssessmentAgent(BaseAgent):
    def __init__(self, model_choice: str = None):
        super().__init__(
            name="HealthAssessment",
            system_prompt=HEALTH_AGENT_SYSTEM_PROMPT,
            model_choice=model_choice
        )

    async def run(self, user_input: str, extra_context: str = "", stream: bool = False) -> AgentResponse:
        risk_result = health_assessment_service.rule_based_assess(user_input)
        advice = await health_assessment_service.generate_health_advice(user_input, risk_result)

        return AgentResponse(
            agent_name=self.name,
            content=advice,
            metadata={
                "risk_level": risk_result["risk_level"],
                "risk_reasons": risk_result["risk_reasons"],
                "need_hospital": risk_result["need_hospital"]
            }
        )

    async def run_stream(self, user_input: str, extra_context: str = "") -> AsyncGenerator[str, None]:
        result = await self.run(user_input, extra_context)
        yield result.content
