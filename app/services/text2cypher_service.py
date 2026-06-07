import re
import json
from typing import Dict, List, Optional, Tuple

import py2neo

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm_service import llm_service, LLMServiceError
from app.services.kg_service import kg_service

logger = get_logger(__name__)

FORBIDDEN_KEYWORDS = ["CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE", "DROP"]

TEXT2CYPHER_SYSTEM_PROMPT = """你是一个 Neo4j Cypher 查询专家。你的任务是将用户的自然语言医学问题转换为 Cypher 查询语句。

## 知识图谱 Schema
节点标签及属性:
- 疾病: 名称, 疾病简介, 疾病病因, 预防措施, 治疗周期, 治愈概率, 疾病易感人群
- 药品: 名称
- 食物: 名称
- 疾病症状: 名称
- 检查项目: 名称
- 科目: 名称
- 治疗方法: 名称

关系类型及方向:
- (疾病)-[疾病使用药品]->(药品)
- (疾病)-[疾病宜吃食物]->(食物)
- (疾病)-[疾病忌吃食物]->(食物)
- (疾病)-[疾病的症状]->(疾病症状)
- (疾病)-[疾病所需检查]->(检查项目)
- (疾病)-[疾病所属科目]->(科目)
- (疾病)-[治疗的方法]->(治疗方法)
- (疾病)-[疾病并发疾病]->(疾病)

## 重要规则
1. 只生成只读 MATCH 查询，禁止 CREATE/DELETE/SET/REMOVE/MERGE/DROP
2. 节点和关系类型必须使用 schema 中定义的名称
3. 使用 $name 参数占位符代替具体的值（如 {名称: $name}），不要硬编码字符串值
4. 返回有意义的结果，通常返回节点名称或属性
5. 多跳查询使用 [*1..3] 限制深度
6. 如果问题涉及多个实体，可用逗号分隔的 $names 列表: WHERE n.名称 IN $names

## 输出格式
请输出一个 JSON 对象:
{
  "cypher": "MATCH ... RETURN ...",
  "params": {"name": "值", ...}
}
只输出 JSON，不要额外解释。"""


def validate_cypher(cypher: str) -> bool:
    """仅允许只读 Cypher 语句"""
    upper = cypher.upper()
    return not any(kw in upper for kw in FORBIDDEN_KEYWORDS)


def _extract_params_from_cypher(cypher: str, entities: Dict[str, str]) -> Dict[str, str]:
    """从 Cypher 语句的参数占位符中提取对应的实体值"""
    params = {}
    param_refs = re.findall(r'\$(\w+)', cypher)
    for ref in param_refs:
        if ref == "name" and "疾病" in entities:
            params["name"] = entities["疾病"]
        elif ref in entities:
            params[ref] = entities[ref]
        elif ref == "names" and "疾病" in entities:
            params["names"] = [entities["疾病"]]
    return params


class Text2CypherService:
    """Text-to-Cypher 服务 —— LLM 生成 Cypher + 安全校验"""

    def __init__(self):
        self.llm = llm_service

    async def generate_cypher(
        self,
        user_query: str,
        entities: Dict[str, str],
        intent_response: str = ""
    ) -> Optional[Dict]:
        """调用 LLM 生成 Cypher 查询，返回 {"cypher": ..., "params": ...} 或 None"""
        schema_str = kg_service.get_schema_summary()
        prompt = (
            f"{TEXT2CYPHER_SYSTEM_PROMPT}\n\n"
            f"## 当前图谱 Schema（动态）\n{schema_str}\n\n"
            f"## 用户问题\n{user_query}\n\n"
            f"## 已识别实体\n{json.dumps(entities, ensure_ascii=False)}\n\n"
            f"## 已识别意图\n{intent_response or '无'}\n\n"
            f"请生成 Cypher 查询 JSON。"
        )

        try:
            raw = await self.llm.generate_completion(prompt)
            # 提取 JSON（LLM 可能包裹在 ```json ... ``` 中）
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if not json_match:
                logger.warning("text2cypher_no_json", raw=raw[:200])
                return None
            result = json.loads(json_match.group(0))
            cypher = result.get("cypher", "")
            params = result.get("params", {})
            if not cypher.strip():
                return None
            # 将 LLM 提供的参数与 NER 实体合并
            merged_params = {**params, **_extract_params_from_cypher(cypher, entities)}
            return {"cypher": cypher, "params": merged_params}
        except (json.JSONDecodeError, LLMServiceError) as e:
            logger.warning("text2cypher_generation_failed", error=str(e))
            return None

    async def execute_text2cypher(
        self,
        user_query: str,
        entities: Dict[str, str],
        intent_response: str = ""
    ) -> Tuple[Optional[str], Optional[List[Dict]]]:
        """完整流程: 生成 → 校验 → 执行 → 返回 (prompt_segment, raw_results)"""
        if not settings.KG_TEXT2CYPHER_ENABLED:
            return None, None

        gen = await self.generate_cypher(user_query, entities, intent_response)
        if not gen:
            return None, None

        cypher = gen["cypher"]
        params = gen["params"]

        if not validate_cypher(cypher):
            logger.warning("text2cypher_blocked", cypher=cypher)
            return None, None

        try:
            results = kg_service.client.run(cypher, **params).data()
            if not results:
                return None, None
            return self._format_results(results, cypher), results
        except py2neo.errors.ClientError as e:
            logger.warning("text2cypher_execution_failed", error=str(e), cypher=cypher)
            return None, None

    @staticmethod
    def _format_results(results: List[Dict], cypher: str) -> str:
        """将查询结果格式化为 Prompt 片段"""
        if not results:
            return ""
        parts = []
        for i, record in enumerate(results[:10]):
            items = [f"{k}: {v}" for k, v in record.items() if v is not None]
            if items:
                parts.append("；".join(items))
        if not parts:
            return ""
        summary = "；\n".join(parts)
        return f"<提示>知识图谱查询结果（text2cypher）：{summary}</提示>"


text2cypher_service = Text2CypherService()
