from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional, Any
from app.services.llm_service import llm_service, LLMServiceError


@dataclass
class AgentResponse:
    agent_name: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model_choice: str = None, domain: str = ""):
        self.name = name
        self.system_prompt = system_prompt
        self.model_choice = model_choice
        self.domain = domain
        self._llm = llm_service

    def _build_messages(self, user_input: str, extra_context: str = "") -> List[Dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if extra_context:
            messages.append({"role": "system", "content": f"<上下文>\n{extra_context}\n</上下文>"})
        messages.append({"role": "user", "content": user_input})
        return messages

    async def run(self, user_input: str, extra_context: str = "", stream: bool = False) -> AgentResponse:
        messages = self._build_messages(user_input, extra_context)
        response = await self._call_llm(messages)
        metadata = {}
        if self.domain:
            metadata["domain"] = self.domain
        return AgentResponse(
            agent_name=self.name,
            content=response,
            metadata=metadata
        )

    async def run_stream(self, user_input: str, extra_context: str = "") -> AsyncGenerator[str, None]:
        messages = self._build_messages(user_input, extra_context)
        async for chunk in self._call_llm_stream(messages):
            yield chunk

    async def _call_llm(self, messages: List[Dict]) -> str:
        prompt = "\n".join([f"[{m['role']}]: {m['content']}" for m in messages])
        try:
            return await self._llm.generate_completion(prompt, self.model_choice)
        except LLMServiceError as e:
            print(f"[ERROR] {self.name} LLM调用失败: {e}")
            return f"抱歉，AI服务暂时不可用，请稍后重试。"

    async def _call_llm_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        prompt = "\n".join([f"[{m['role']}]: {m['content']}" for m in messages])
        try:
            async for chunk in self._llm.chat(prompt, self.model_choice, stream=True):
                yield chunk
        except LLMServiceError as e:
            print(f"[ERROR] {self.name} LLM流式调用失败: {e}")
            yield "抱歉，AI服务暂时不可用，请稍后重试。"
