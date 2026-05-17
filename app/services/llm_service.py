from typing import AsyncGenerator, Dict, List
from openai import OpenAI
from app.core.config import settings


class LLMServiceError(Exception):
    """LLM 调用异常"""
    pass


class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.default_model = settings.DEEPSEEK_MODEL

    def _get_model(self, model_choice: str = None) -> str:
        """模型名称兼容性处理"""
        if model_choice is None or ":" in model_choice or "qwen" in model_choice.lower():
            return self.default_model
        return model_choice

    # ── New structured-message methods ──────────────────────────────

    async def chat_with_messages(
        self,
        messages: List[Dict[str, str]],
        model_choice: str = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """通用聊天接口 — 直接传递 OpenAI 格式 messages 列表"""
        model = self._get_model(model_choice)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream
            )
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] LLM调用失败: {str(e)}")
            yield f"抱歉，AI服务暂时不可用。错误详情: {str(e)}"

    async def generate_completion_with_messages(
        self,
        messages: List[Dict[str, str]],
        model_choice: str = None
    ) -> str:
        """非流式文本生成 — 直接传递 OpenAI 格式 messages 列表"""
        model = self._get_model(model_choice)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False
            )
            content = response.choices[0].message.content
            return content if content else ""
        except Exception as e:
            print(f"[ERROR] LLM生成失败: {str(e)}")
            raise LLMServiceError(f"LLM调用失败: {str(e)}") from e

    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        model_choice: str = None,
        stream: bool = False
    ):
        """带工具调用的聊天接口 — 返回完整响应对象（非流式）或流式生成器"""
        model = self._get_model(model_choice)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                stream=stream
            )
            return response
        except Exception as e:
            print(f"[ERROR] LLM工具调用失败: {str(e)}")
            raise LLMServiceError(f"LLM工具调用失败: {str(e)}") from e

    # ── Deprecated methods (kept for backward compatibility) ────────

    async def chat(self, prompt: str, model_choice: str = None, stream: bool = True):
        """@deprecated 使用 chat_with_messages() 代替"""
        model = self._get_model(model_choice)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=stream
            )
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] LLM调用失败: {str(e)}")
            yield f"抱歉，AI服务暂时不可用。错误详情: {str(e)}"

    async def generate_completion(self, prompt: str, model_choice: str = None) -> str:
        """@deprecated 使用 generate_completion_with_messages() 代替"""
        model = self._get_model(model_choice)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] LLM生成失败: {str(e)}")
            raise LLMServiceError(f"LLM调用失败: {str(e)}") from e


llm_service = LLMService()
