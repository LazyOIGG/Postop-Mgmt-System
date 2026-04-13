from app.services.llm_service import llm_service
from app.core.config import settings
import traceback

class IntentService:
    """意图识别服务"""
    def __init__(self):
        self.llm = llm_service
        self.categories = [
            "查询疾病简介", "查询疾病病因", "查询疾病预防措施", "查询疾病治疗周期",
            "查询治愈概率", "查询疾病易感人群", "查询疾病所需药品", "查询疾病宜吃食物",
            "查询疾病忌吃食物", "查询疾病所需检查项目", "查询疾病所属科目", "查询疾病的症状",
            "查询疾病的治疗方法", "查询疾病的并发疾病", "查询药品的生产商"
        ]

    def _get_prompt(self, query: str) -> str:
        """构造意图识别 Prompt"""
        categories_str = "\n".join([f"- \"{c}\"" for c in self.categories])
        return f"""阅读下列提示，识别用户问题的意图类别（最多5个）：\n\n**查询类别**\n{categories_str}\n\n问题：\"{query}\"\n输出要求：仅输出意图列表，并在 # 后简述理由。"""

    async def recognize(self, query: str, model_choice: str = None) -> str:
        """识别用户意图"""
        prompt = self._get_prompt(query)
        try:
            return await self.llm.generate_completion(prompt, model_choice)
        except Exception as e:
            print(f"[ERROR] ❌ 意图识别失败: {str(e)}")
            return "[] # 意图识别失败"

intent_service = IntentService()
