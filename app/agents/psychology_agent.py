from app.agents.base import BaseAgent, AgentResponse

PSYCHOLOGY_SYSTEM_PROMPT = """你是一个术后心理辅导与情绪缓解助手。你的职责是帮助术后患者应对心理和情绪方面的困扰：

1. 术后焦虑 — 对恢复进展、并发症的担忧
2. 情绪低落 — 长期卧床、活动受限导致的抑郁情绪
3. 睡眠问题 — 术后疼痛或焦虑引起的失眠
4. 康复压力 — 对康复训练、饮食控制的抵触和压力
5. 社交隔离感 — 住院或居家恢复期间的孤独感
6. 对未来的恐惧 — 担心复发、无法恢复正常生活

回答要求：
- 温暖共情，先倾听和认可患者的感受
- 提供科学、实用的情绪缓解方法（呼吸练习、正念放松、渐进式肌肉放松等）
- 结合术后恢复场景给出针对性建议
- 鼓励患者与家人、医护人员多沟通
- 如症状严重，明确建议寻求专业心理咨询或精神科帮助
- 语言通俗柔和，避免说教
- 不要做任何临床诊断"""


class PsychologyAgent(BaseAgent):
    def __init__(self, model_choice: str = None):
        super().__init__(
            name="Psychology",
            system_prompt=PSYCHOLOGY_SYSTEM_PROMPT,
            model_choice=model_choice
        )

    async def run(self, user_input: str, extra_context: str = "", stream: bool = False) -> AgentResponse:
        messages = self._build_messages(user_input, extra_context)
        response = await self._call_llm(messages)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            metadata={"domain": "psychology"}
        )

    async def run_stream(self, user_input: str, extra_context: str = ""):
        messages = self._build_messages(user_input, extra_context)
        async for chunk in self._call_llm_stream(messages):
            yield chunk
