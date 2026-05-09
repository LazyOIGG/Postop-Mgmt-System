from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable, Dict, List, Optional, Any
from app.services.llm_service import llm_service


@dataclass
class AgentResponse:
    agent_name: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model_choice: str = None):
        self.name = name
        self.system_prompt = system_prompt
        self.model_choice = model_choice
        self._tools: Dict[str, Callable] = {}
        self._llm = llm_service

    def register_tool(self, name: str, func: Callable):
        self._tools[name] = func

    def _build_messages(self, user_input: str, extra_context: str = "") -> List[Dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if extra_context:
            messages.append({"role": "system", "content": f"<上下文>\n{extra_context}\n</上下文>"})
        messages.append({"role": "user", "content": user_input})
        return messages

    async def run(self, user_input: str, extra_context: str = "", stream: bool = False) -> AgentResponse:
        raise NotImplementedError

    async def run_stream(self, user_input: str, extra_context: str = "") -> AsyncGenerator[str, None]:
        raise NotImplementedError

    async def _call_llm(self, messages: List[Dict]) -> str:
        prompt = "\n".join([f"[{m['role']}]: {m['content']}" for m in messages])
        return await self._llm.generate_completion(prompt, self.model_choice)

    async def _call_llm_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        prompt = "\n".join([f"[{m['role']}]: {m['content']}" for m in messages])
        async for chunk in self._llm.chat(prompt, self.model_choice, stream=True):
            yield chunk
