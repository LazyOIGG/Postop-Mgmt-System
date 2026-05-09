import json
from typing import AsyncGenerator, Dict
from app.agents.base import AgentResponse
from app.agents.coordinator import CoordinatorAgent
from app.agents.medical_qa_agent import MedicalQAAgent
from app.agents.health_agent import HealthAssessmentAgent
from app.agents.reminder_agent import ReminderAgent
from app.agents.psychology_agent import PsychologyAgent

AGENT_DISPLAY_NAMES = {
    "MedicalQA": "医学知识问答",
    "HealthAssessment": "健康风险评估",
    "Reminder": "用药复查提醒",
    "Psychology": "心理辅导缓解",
}


def _agent_label(agent_name: str) -> str:
    display = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
    return f"> 🤖 **{display}** 智能体为您服务\n\n"


class MultiAgentOrchestrator:
    def __init__(self, model_choice: str = None):
        self.model_choice = model_choice
        self.coordinator = CoordinatorAgent(model_choice=model_choice)
        self.agents = {
            "medical_qa": MedicalQAAgent(model_choice=model_choice),
            "health_assessment": HealthAssessmentAgent(model_choice=model_choice),
            "reminder": ReminderAgent(model_choice=model_choice),
            "psychology": PsychologyAgent(model_choice=model_choice),
        }

    def register_agent(self, name: str, agent):
        self.agents[name] = agent

    async def process(self, user_input: str, username: str = None) -> Dict:
        route_result = await self.coordinator.run(user_input)
        routed_agent_name = route_result.content
        route_meta = route_result.metadata

        agent = self.agents.get(routed_agent_name)
        if agent is None:
            agent = self.agents["medical_qa"]

        agent_result = await agent.run(user_input)

        return {
            "content": _agent_label(agent_result.agent_name) + agent_result.content,
            "agent": agent_result.agent_name,
            "routed_by": {
                "agent": routed_agent_name,
                "reason": route_meta.get("reason", ""),
                "confidence": route_meta.get("confidence", 0.5)
            },
            "metadata": agent_result.metadata,
            "success": agent_result.success,
            "error": agent_result.error
        }

    async def process_stream(self, user_input: str, username: str = None) -> AsyncGenerator[str, None]:
        route_result = await self.coordinator.run(user_input)
        routed_agent_name = route_result.content
        route_meta = route_result.metadata

        agent = self.agents.get(routed_agent_name)
        if agent is None:
            agent = self.agents["medical_qa"]

        yield json.dumps({
            "type": "chunk",
            "content": _agent_label(agent.name)
        }, ensure_ascii=False) + "\n"

        yield json.dumps({
            "type": "route",
            "agent": routed_agent_name,
            "reason": route_meta.get("reason", ""),
            "confidence": route_meta.get("confidence", 0.5)
        }, ensure_ascii=False) + "\n"

        async for chunk in agent.run_stream(user_input):
            yield json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False) + "\n"

        yield json.dumps({"type": "complete"}, ensure_ascii=False) + "\n"


orchestrator = MultiAgentOrchestrator()
