from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional, Any
from app.services.llm_service import llm_service, LLMServiceError
from app.core.config import settings


@dataclass
class AgentResponse:
    agent_name: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    tools: List[str] = []

    def __init__(self, name: str, system_prompt: str, model_choice: str = None, domain: str = ""):
        self.name = name
        self.system_prompt = system_prompt
        self.model_choice = model_choice
        self.domain = domain
        self._llm = llm_service

    def _build_messages(
        self,
        user_input: str,
        extra_context: str = "",
        history: List[Dict[str, str]] = None
    ) -> List[Dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if extra_context:
            messages.append({"role": "system", "content": f"<上下文>\n{extra_context}\n</上下文>"})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        return messages

    async def run(
        self,
        user_input: str,
        extra_context: str = "",
        stream: bool = False,
        history: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> AgentResponse:
        if tools and self.tools:
            response = await self._call_llm_with_tools(user_input, extra_context, history, tools)
            return AgentResponse(
                agent_name=self.name,
                content=response,
                metadata={"domain": self.domain} if self.domain else {}
            )

        messages = self._build_messages(user_input, extra_context, history)
        response = await self._call_llm(messages)
        metadata = {}
        if self.domain:
            metadata["domain"] = self.domain
        return AgentResponse(
            agent_name=self.name,
            content=response,
            metadata=metadata
        )

    async def run_stream(
        self,
        user_input: str,
        extra_context: str = "",
        history: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        if tools and self.tools:
            result = await self._call_llm_with_tools(user_input, extra_context, history, tools)
            yield result
            return

        messages = self._build_messages(user_input, extra_context, history)
        async for chunk in self._call_llm_stream(messages):
            yield chunk

    # ── LLM call helpers ───────────────────────────────────────────

    async def _call_llm(self, messages: List[Dict]) -> str:
        try:
            return await self._llm.generate_completion_with_messages(messages, self.model_choice)
        except LLMServiceError as e:
            print(f"[ERROR] {self.name} LLM调用失败: {e}")
            return "抱歉，AI服务暂时不可用，请稍后重试。"

    async def _call_llm_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        try:
            async for chunk in self._llm.chat_with_messages(messages, self.model_choice, stream=True):
                yield chunk
        except LLMServiceError as e:
            print(f"[ERROR] {self.name} LLM流式调用失败: {e}")
            yield "抱歉，AI服务暂时不可用，请稍后重试。"

    async def _call_llm_with_tools(
        self,
        user_input: str,
        extra_context: str = "",
        history: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> str:
        messages = self._build_messages(user_input, extra_context, history)
        max_rounds = getattr(settings, 'MAX_TOOL_CALL_ROUNDS', 3)

        for round_num in range(max_rounds):
            response = await self._llm.chat_with_tools(
                messages, tools, self.model_choice, stream=False
            )
            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                assistant_msg = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in msg.tool_calls
                    ]
                }
                # DeepSeek thinking mode: reasoning_content must be passed back
                reasoning = getattr(msg, 'reasoning_content', None)
                if reasoning:
                    assistant_msg["reasoning_content"] = reasoning
                messages.append(assistant_msg)

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        import json
                        args = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    tool_result = await self._execute_tool(tool_name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result
                    })
            else:
                return msg.content or ""

        # Max rounds reached — force final response without tools
        messages.append({"role": "user", "content": "请基于以上工具调用结果给出最终回答。"})
        try:
            result = await self._llm.generate_completion_with_messages(messages, self.model_choice)
            return result
        except LLMServiceError:
            return "抱歉，AI服务暂时不可用，请稍后重试。"

    async def _execute_tool(self, tool_name: str, args: Dict) -> str:
        """Execute a tool by name. Override in subclasses or use ToolRegistry."""
        try:
            from app.agents.tools import tool_registry
            return await tool_registry.execute(tool_name, args)
        except Exception as e:
            return f"[工具执行错误] {tool_name}: {str(e)}"
