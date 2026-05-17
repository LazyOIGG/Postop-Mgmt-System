from typing import AsyncGenerator, Dict, List
from app.agents.base import BaseAgent, AgentResponse
from app.services.health_assessment_service import health_assessment_service

HEALTH_AGENT_SYSTEM_PROMPT = """你是一个术后健康风险评估助手。你的职责是：
1. 分析患者描述的身体症状和不适
2. 根据风险等级（高风险/中风险/低风险）给出对应的健康建议
3. 判断是否需要建议患者尽快就医
4. 提供术后恢复指导

你可以调用以下工具：
- get_recent_checkins：查询患者最近的健康打卡记录
- get_checkin_trend：分析患者近期健康趋势

重要规则 — 何时使用工具：
- 用户要求"查看最近的打卡记录"、"分析趋势"等 → 使用工具
- 用户在对话中已经告诉过你的信息（如体温、症状）→ 直接引用对话历史回答，不要调用工具
- 你无法确定的信息 → 使用工具查询
- 优先从对话历史中获取信息，避免重复查询

回答要求：
- 结构清晰：先总结情况，再给出建议措施
- 高风险情况必须明确建议就医
- 语言通俗易懂，避免引起不必要的恐慌
- 不要过度诊断，必要时建议咨询主治医生"""


class HealthAssessmentAgent(BaseAgent):
    tools = ["get_recent_checkins", "get_checkin_trend"]

    def __init__(self, model_choice: str = None):
        super().__init__(
            name="HealthAssessment",
            system_prompt=HEALTH_AGENT_SYSTEM_PROMPT,
            model_choice=model_choice
        )

    async def run(
        self,
        user_input: str,
        extra_context: str = "",
        stream: bool = False,
        history: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> AgentResponse:
        risk_result = health_assessment_service.rule_based_assess(user_input)

        if tools and self.tools:
            ctx = extra_context or ""
            if risk_result["risk_reasons"]:
                ctx += f"\n风险评估: {risk_result['risk_level']} | 原因: {';'.join(risk_result['risk_reasons'])}"
            response = await self._call_llm_with_tools(user_input, ctx, history, tools)
            return AgentResponse(
                agent_name=self.name,
                content=response,
                metadata={
                    "risk_level": risk_result["risk_level"],
                    "risk_reasons": risk_result["risk_reasons"],
                    "need_hospital": risk_result["need_hospital"]
                }
            )

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

    async def run_stream(
        self,
        user_input: str,
        extra_context: str = "",
        history: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        if tools and self.tools:
            result = await self.run(user_input, extra_context, False, history, tools)
            yield result.content
            return

        result = await self.run(user_input, extra_context)
        yield result.content
