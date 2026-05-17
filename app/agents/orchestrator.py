import json
from typing import AsyncGenerator, Dict, List
from app.agents.base import AgentResponse
from app.agents.coordinator import CoordinatorAgent
from app.agents.medical_qa_agent import MedicalQAAgent
from app.agents.health_agent import HealthAssessmentAgent
from app.agents.reminder_agent import ReminderAgent
from app.agents.psychology_agent import PsychologyAgent
from app.agents.rehab_plan_agent import RehabPlanAgent
from app.core.config import settings
from app.db.session import db_instance

AGENT_DISPLAY_NAMES = {
    "MedicalQA": "医学知识问答",
    "HealthAssessment": "健康风险评估",
    "Reminder": "用药复查提醒",
    "Psychology": "心理辅导缓解",
    "RehabPlan": "康复计划管理",
}


def _agent_label(agent_name: str) -> str:
    display = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
    return f"> 🤖 **{display}** 智能体为您服务\n\n"


def _count_chinese_chars(text: str) -> int:
    """统计中文字符数量"""
    return sum(1 for ch in text if '一' <= ch <= '鿿')


class MultiAgentOrchestrator:
    def __init__(self, model_choice: str = None):
        self.model_choice = model_choice
        self.coordinator = CoordinatorAgent(model_choice=model_choice)
        self.agents = {
            "medical_qa": MedicalQAAgent(model_choice=model_choice),
            "health_assessment": HealthAssessmentAgent(model_choice=model_choice),
            "reminder": ReminderAgent(model_choice=model_choice),
            "psychology": PsychologyAgent(model_choice=model_choice),
            "rehab_plan": RehabPlanAgent(model_choice=model_choice),
        }

    def register_agent(self, name: str, agent) -> None:
        self.agents[name] = agent

    # ── Conversation history ───────────────────────────────────────

    async def _load_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        if not session_id:
            return []
        try:
            raw_messages = db_instance.get_session_messages(int(session_id))
        except Exception as e:
            print(f"[WARN] 加载对话历史失败: {e}")
            return []

        if not raw_messages:
            return []

        # Limit to recent turns
        max_msgs = settings.MAX_CONVERSATION_HISTORY_TURNS * 2
        raw_messages = raw_messages[-max_msgs:]

        history = []
        total_chars = 0
        for msg in raw_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                history.append({"role": role, "content": content})
                total_chars += _count_chinese_chars(content)

        print(f"[HISTORY] session={session_id}, 加载 {len(history)} 条消息, 中文约 {total_chars} 字")
        if total_chars > settings.CONVERSATION_SUMMARY_THRESHOLD_CHARS:
            summary = await self._summarize_history(history)
            print(f"[HISTORY] 触发摘要压缩, 原文 {total_chars} 字 -> 摘要 {len(summary)} 字")
            return [{"role": "system", "content": f"<对话摘要>\n{summary}\n</对话摘要>"}]

        return history

    async def _summarize_history(self, history: List[Dict[str, str]]) -> str:
        """压缩对话历史为摘要"""
        lines = []
        for msg in history[-settings.MAX_CONVERSATION_HISTORY_TURNS * 2:]:
            role_label = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"[{role_label}]: {msg['content']}")
        conversation_text = "\n".join(lines)

        try:
            summary_prompt = (
                "请将以下对话历史压缩为一段简洁的摘要（200字以内），"
                "保留关键信息（症状、用药、建议、时间等）：\n\n" + conversation_text
            )
            from app.services.llm_service import llm_service
            return await llm_service.generate_completion(summary_prompt, self.model_choice)
        except Exception:
            return f"对话历史包含 {len(history)} 条消息，主要涉及健康管理相关咨询。"

    # ── Tool resolution ────────────────────────────────────────────

    def _get_tools_for_agent(self, agent) -> List[Dict]:
        tool_names = getattr(agent, 'tools', [])
        if not tool_names:
            return None
        try:
            from app.agents.tools import tool_registry
            return tool_registry.get_openai_tools(tool_names)
        except Exception:
            return None

    # ── Process ────────────────────────────────────────────────────

    async def process(
        self,
        user_input: str,
        username: str = None,
        session_id: str = None
    ) -> Dict:
        route_result = await self.coordinator.run(user_input)
        routed_agent_name = route_result.content
        route_meta = route_result.metadata

        agent = self.agents.get(routed_agent_name)
        if agent is None:
            agent = self.agents["medical_qa"]

        history = await self._load_conversation_history(session_id)
        tools = self._get_tools_for_agent(agent)

        # Inject username so tools can use it without LLM asking
        ctx = f"当前用户: {username}" if username else ""

        agent_result = await agent.run(
            user_input,
            extra_context=ctx,
            history=history,
            tools=tools
        )

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

    async def process_stream(
        self,
        user_input: str,
        username: str = None,
        session_id: str = None
    ) -> AsyncGenerator[str, None]:
        route_result = await self.coordinator.run(user_input)
        routed_agent_name = route_result.content
        route_meta = route_result.metadata

        agent = self.agents.get(routed_agent_name)
        if agent is None:
            agent = self.agents["medical_qa"]

        history = await self._load_conversation_history(session_id)
        tools = self._get_tools_for_agent(agent)

        # Inject username so tools can use it without LLM asking
        ctx = f"当前用户: {username}" if username else ""

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

        async for chunk in agent.run_stream(user_input, extra_context=ctx, history=history, tools=tools):
            yield json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False) + "\n"

        yield json.dumps({"type": "complete"}, ensure_ascii=False) + "\n"


orchestrator = MultiAgentOrchestrator()
