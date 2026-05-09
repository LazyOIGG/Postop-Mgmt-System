import re
from typing import AsyncGenerator
from app.agents.base import BaseAgent, AgentResponse
from app.services.ner_service import ner_service
from app.services.intent_service import intent_service
from app.services.kg_service import kg_service


MEDICAL_QA_SYSTEM_PROMPT = """你是一个术后管理医学知识问答助手。你的职责是回答患者关于疾病、药品、食物、检查、症状、治疗等方面的医学知识问题。

回答要求：
- 基于知识图谱数据或医学知识给出准确回答
- 如果涉及术后恢复，请结合术后管理场景给出建议
- 语言通俗易懂，结构清晰
- 如果信息不足，请诚实说明"""


class MedicalQAAgent(BaseAgent):
    def __init__(self, model_choice: str = None):
        super().__init__(
            name="MedicalQA",
            system_prompt=MEDICAL_QA_SYSTEM_PROMPT,
            model_choice=model_choice
        )

    async def run(self, user_input: str, extra_context: str = "", stream: bool = False) -> AgentResponse:
        entities = ner_service.recognize(user_input)
        intent_res = await intent_service.recognize(user_input, self.model_choice)
        prompt, yitu, entities, has_kg = kg_service.generate_enhanced_prompt(intent_res, user_input, entities)

        full_response = ""
        async for chunk in self._llm.chat(prompt, self.model_choice, stream=True):
            full_response += chunk

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

    async def run_stream(self, user_input: str, extra_context: str = "") -> AsyncGenerator[str, None]:
        entities = ner_service.recognize(user_input)
        intent_res = await intent_service.recognize(user_input, self.model_choice)
        prompt, yitu, entities, has_kg = kg_service.generate_enhanced_prompt(intent_res, user_input, entities)

        async for chunk in self._llm.chat(prompt, self.model_choice, stream=True):
            yield chunk
