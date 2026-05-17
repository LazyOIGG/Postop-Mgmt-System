import re
from typing import AsyncGenerator, Dict, List
from app.agents.base import BaseAgent, AgentResponse
from app.services.ner_service import ner_service
from app.services.intent_service import intent_service
from app.services.kg_service import kg_service


MEDICAL_QA_SYSTEM_PROMPT = """你是一个专业的医学知识问答助手。你的职责是回答用户关于疾病、药品、食物、检查、症状、治疗等方面的医学知识问题。

你可以调用以下工具：
- query_drug_info：查询药品详细信息
- query_disease_symptoms：查询疾病症状信息
- create_reminder：当用户要求创建提醒时调用
- list_reminders：查看用户已有提醒
- update_reminder_status：更新提醒状态

重要规则：
- 用户在对话历史中已经告诉过你的信息 → 直接引用，不要调用工具重复查询
- 需要新的专业知识或执行实际操作（创建提醒、查询药品等）→ 使用工具
- 用户名从上下文（<上下文> 标签）中获取，不要反问用户

回答要求：
- 基于知识图谱数据或医学知识给出准确回答
- 语言通俗易懂，结构清晰
- 如果信息不足，请诚实说明"""


class MedicalQAAgent(BaseAgent):
    tools = ["query_drug_info", "query_disease_symptoms", "create_reminder", "list_reminders", "update_reminder_status"]

    def __init__(self, model_choice: str = None):
        super().__init__(
            name="MedicalQA",
            system_prompt=MEDICAL_QA_SYSTEM_PROMPT,
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
        entities = ner_service.recognize(user_input)
        intent_res = await intent_service.recognize(user_input, self.model_choice)
        prompt, yitu, entities, has_kg = kg_service.generate_enhanced_prompt(intent_res, user_input, entities)

        # When tools are active, route through the tool-call loop
        if tools and self.tools:
            response = await self._call_llm_with_tools(prompt, extra_context, history, tools)
            return AgentResponse(
                agent_name=self.name,
                content=response,
                metadata={
                    "entities": str(entities),
                    "intents": yitu,
                    "has_kg": has_kg
                }
            )

        messages = self._build_messages(prompt, extra_context, history)
        full_response = await self._call_llm(messages)

        knowledge = "\n".join([
            f"提示{i+1}: {k}"
            for i, k in enumerate(re.findall(r'<提示>(.*?)</提示>', prompt))
            if len(k) >= 3
        ])

        return AgentResponse(
            agent_name=self.name,
            content=full_response,
            metadata={
                "entities": str(entities),
                "intents": yitu,
                "knowledge": knowledge,
                "has_kg": has_kg,
                "prompt": prompt
            }
        )

    async def run_stream(
        self,
        user_input: str,
        extra_context: str = "",
        history: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        entities = ner_service.recognize(user_input)
        intent_res = await intent_service.recognize(user_input, self.model_choice)
        prompt, yitu, entities, has_kg = kg_service.generate_enhanced_prompt(intent_res, user_input, entities)

        if tools and self.tools:
            result = await self._call_llm_with_tools(prompt, extra_context, history, tools)
            yield result
            return

        messages = self._build_messages(prompt, extra_context, history)
        async for chunk in self._call_llm_stream(messages):
            yield chunk
