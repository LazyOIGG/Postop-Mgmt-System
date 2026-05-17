import json
from app.agents.base import BaseAgent, AgentResponse

COORDINATOR_SYSTEM_PROMPT = """你是一个术后管理多智能体系统的协调者（Coordinator）。你的任务是分析用户输入，判断应该路由到哪个专业智能体处理。

可路由的智能体及其职责：

1. **medical_qa** — 处理医学知识问答：
   - 疾病查询（简介、病因、症状、治疗、预防、并发症等）
   - 药品查询（用法、生产商、注意事项等）
   - 食物查询（宜吃、忌吃等）
   - 检查项目、所属科目等

2. **health_assessment** — 处理健康风险评估：
   - 患者描述身体不适、症状变化
   - 询问是否需要就医
   - 术后恢复情况评估
   - 体温、血压等生命体征异常

3. **reminder** — 处理提醒管理（重要：任何涉及提醒的操作都路由到这里）：
   - 创建/查看/修改/删除用药提醒（关键词：创建提醒、设置提醒、帮我提醒、吃药提醒、服药提醒）
   - 创建/查看/修改/删除复查提醒
   - 每日健康打卡相关
   - 即使用户消息中包含药品名称（如阿莫西林），如果核心意图是创建提醒，也必须路由到 reminder

4. **psychology** — 处理心理情绪问题：
   - 术后焦虑、紧张、恐惧
   - 情绪低落、抑郁、失眠
   - 康复压力、社交孤独感
   - 对并发症或复发的担忧
   - 需要情绪支持和心理疏导

5. **rehab_plan** — 处理康复计划管理：
   - 生成术后康复计划（关键词：康复计划、制定计划、术后恢复方案、康复规划）
   - 查看康复计划进度和今日任务
   - 完成康复任务打卡
   - 康复阶段调整

6. **general** — 处理其他一般性问题

路由判断优先级：先看核心意图（用户想做什么），再看内容细节。例如"帮我创建吃阿莫西林的提醒"的核心意图是创建提醒 → 路由到 reminder。

输出格式必须是严格的JSON：{"agent": "<agent_name>", "reason": "<简短理由>", "confidence": <0.0-1.0>}"""


class CoordinatorAgent(BaseAgent):
    def __init__(self, model_choice: str = None):
        super().__init__(
            name="Coordinator",
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            model_choice=model_choice
        )

    async def run(self, user_input: str, extra_context: str = "", stream: bool = False) -> AgentResponse:
        messages = self._build_messages(user_input, extra_context)
        raw = await self._call_llm(messages)

        try:
            json_match = raw.strip()
            if "```json" in json_match:
                json_match = json_match.split("```json")[1].split("```")[0].strip()
            elif "```" in json_match:
                json_match = json_match.split("```")[1].split("```")[0].strip()

            result = json.loads(json_match)
            agent_name = result.get("agent", "general")
            reason = result.get("reason", "")
            confidence = result.get("confidence", 0.5)
        except (json.JSONDecodeError, KeyError):
            agent_name = "medical_qa"
            reason = "解析失败，默认路由到医学问答"
            confidence = 0.3

        return AgentResponse(
            agent_name=self.name,
            content=agent_name,
            metadata={
                "routed_agent": agent_name,
                "reason": reason,
                "confidence": confidence,
                "raw_response": raw
            }
        )

    async def run_stream(self, user_input: str, extra_context: str = ""):
        yield (await self.run(user_input, extra_context)).content
