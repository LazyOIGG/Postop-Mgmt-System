from openai import OpenAI
from app.core.config import settings
import traceback

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

    async def chat(self, prompt: str, model_choice: str = None, stream: bool = True):
        """通用聊天接口"""
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
            print(f"[ERROR] ❌ LLM调用失败: {str(e)}")
            yield f"抱歉，AI服务暂时不可用。错误详情: {str(e)}"

    async def generate_completion(self, prompt: str, model_choice: str = None) -> str:
        """非流式文本生成"""
        model = self._get_model(model_choice)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] ❌ LLM生成失败: {str(e)}")
            return ""

llm_service = LLMService()
