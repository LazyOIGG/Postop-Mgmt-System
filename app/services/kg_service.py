import py2neo
import random
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_PROPERTIES = {"疾病简介", "疾病病因", "预防措施", "治疗周期", "治愈概率", "疾病易感人群"}
ALLOWED_RELATIONSHIPS = {"疾病使用药品", "疾病宜吃食物", "疾病忌吃食物", "疾病所需检查", "疾病所属科目", "疾病的症状", "治疗的方法", "疾病并发疾病"}
ALLOWED_LABELS = {"药品", "食物", "检查项目", "科目", "疾病症状", "治疗方法", "疾病"}


class KGService:
    """知识图谱服务"""
    def __init__(self):
        try:
            self.client = py2neo.Graph(
                settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
                name=settings.NEO4J_NAME
            )
            logger.info("neo4j_connected")
        except Exception as e:
            logger.error("neo4j_connection_failed", error=str(e))
            self.client = None

    def add_shuxing_prompt(self, entity: str, shuxing: str) -> str:
        """查询疾病属性并生成提示"""
        if self.client is None: return ""
        if shuxing not in ALLOWED_PROPERTIES:
            raise ValueError(f"非法属性: {shuxing}")
        try:
            sql_q = "match (a:疾病{名称:$name}) return a." + shuxing
            res = self.client.run(sql_q, name=entity).data()
            if res:
                content = "".join(res[0].values())
                return f"<提示>用户对{entity}有查询{shuxing}需求，知识库内容：{content}</提示>"
        except py2neo.errors.ClientError as e:
            logger.warning("attribute_query_failed", attribute=shuxing, error=str(e))
        return ""

    def add_lianxi_prompt(self, entity: str, lianxi: str, target: str) -> str:
        """查询疾病联系并生成提示"""
        if self.client is None: return ""
        if lianxi not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"非法关系: {lianxi}")
        if target not in ALLOWED_LABELS:
            raise ValueError(f"非法标签: {target}")
        try:
            sql_q = f"match (a:疾病{{名称:$name}})-[r:{lianxi}]->(b:{target}) return b.名称"
            res = self.client.run(sql_q, name=entity).data()
            if res:
                names = "、".join([list(data.values())[0] for data in res])
                return f"<提示>用户对{entity}有查询{lianxi}需求，知识库内容：{names}</提示>"
        except py2neo.errors.ClientError as e:
            logger.warning("relation_query_failed", relation=lianxi, error=str(e))
        return ""

    def generate_enhanced_prompt(self, intent_response: str, query: str, entities: Dict) -> Tuple[str, str, Dict, bool]:
        """根据意图和实体生成增强 Prompt"""
        neo4j_prompt = '<指令>你是一个专业的健康管理助手。回答必须严格基于给定的提示内容，不可自由发挥。如无信息，请回答”根据已知信息无法回答该问题”。</指令>'
        has_kg = False
        
        # 症状推测逻辑
        if '疾病症状' in entities and '疾病' not in entities and self.client:
            try:
                sql_q = "match (a:疾病)-[r:疾病的症状]->(b:疾病症状 {名称:$name}) return a.名称"
                res = [v for d in self.client.run(sql_q, name=entities['疾病症状']).data() for v in d.values()]
                if res:
                    has_kg = True
                    entities['疾病'] = random.choice(res)
                    neo4j_prompt += f"<提示>基于{entities['疾病症状']}，推测可能是：{'、'.join(res)}。请告知用户这仅为推测。</提示>"
            except py2neo.errors.ClientError as e:
                logger.error("symptom_inference_failed", error=str(e))

        # 意图映射查询
        intent_map = {
            "简介": ("查询疾病简介", "疾病简介", None), "病因": ("查询疾病病因", "疾病病因", None),
            "预防": ("查询疾病预防措施", "预防措施", None), "治疗周期": ("查询疾病治疗周期", "治疗周期", None),
            "治愈概率": ("查询治愈概率", "治愈概率", None), "易感人群": ("查询疾病易感人群", "疾病易感人群", None),
            "药品": ("查询疾病所需药品", "疾病使用药品", "药品"), "宜吃食物": ("查询疾病宜吃食物", "疾病宜吃食物", "食物"),
            "忌吃食物": ("查询疾病忌吃食物", "疾病忌吃食物", "食物"), "检查项目": ("查询疾病所需检查项目", "疾病所需检查", "检查项目"),
            "所属科目": ("查询疾病所属科目", "疾病所属科目", "科目"), "症状": ("查询疾病的症状", "疾病的症状", "疾病症状"),
            "治疗": ("查询疾病的治疗方法", "治疗的方法", "治疗方法"), "并发": ("查询疾病的并发疾病", "疾病并发疾病", "疾病")
        }
        
        yitu_list = []
        for key, (intent, prop, target) in intent_map.items():
            if key in intent_response.lower() and '疾病' in entities:
                p = self.add_lianxi_prompt(entities['疾病'], prop, target) if target else self.add_shuxing_prompt(entities['疾病'], prop)
                if p: 
                    neo4j_prompt += p
                    has_kg = True
                    yitu_list.append(intent)

        # 最终 Prompt 构造
        if has_kg:
            prompt = f"{neo4j_prompt}\n<用户问题>{query}</用户问题>\n<注意>请将提示知识整理成结构清晰、专业的回答，并在末尾标注“(本回答基于知识图谱生成)”。</注意>"
        else:
            prompt = f"<指令>你是一个健康管理助手。请直接回答用户问题，并确保准确专业。</指令>\n<用户问题>{query}</用户问题>\n<注意>末尾请标注“(本回答由大语言模型生成)”。</注意>"
        
        return prompt, "、".join(yitu_list), entities, has_kg

    def query(self, cypher_query: str) -> List[Dict]:
        """执行原生 Cypher 查询"""
        if self.client is None: return []
        try:
            return self.client.run(cypher_query).data()
        except py2neo.errors.ClientError as e:
            logger.error("cypher_query_failed", error=str(e))
            return []

    def multi_hop_query(self, entity_name: str, max_hops: int = 3):
        """多跳查询，返回子图用于前端可视化"""
        if self.client is None:
            return {"nodes": [], "edges": []}
        try:
            query = f"""
                MATCH path = (n)-[*1..{max_hops}]-(m)
                WHERE n.名称 = $name
                RETURN path LIMIT 100
            """
            result = self.client.run(query, name=entity_name).data()
            nodes = {}
            edges = []

            for record in result:
                path = record.get('path')
                if not path:
                    continue
                for node in path.nodes:
                    node_id = str(node.identity)
                    if node_id not in nodes:
                        label = list(node.labels)[0] if node.labels else 'Unknown'
                        name = node.get('名称', node_id)
                        nodes[node_id] = {"id": node_id, "name": name, "labels": [label]}
                for rel in path.relationships:
                    src = str(rel.start_node.identity)
                    tgt = str(rel.end_node.identity)
                    edges.append({"source": src, "target": tgt, "type": type(rel).__name__})

            return {"nodes": list(nodes.values()), "edges": edges}
        except Exception as e:
            logger.error("multi_hop_query_failed", error=str(e))
            return {"nodes": [], "edges": []}

    def get_schema(self) -> dict:
        """获取知识图谱 Schema"""
        if self.client is None:
            return {"node_types": [], "relationship_types": []}
        try:
            node_query = "CALL db.labels()"
            rel_query = "CALL db.relationshipTypes()"
            node_types = [r['label'] for r in self.client.run(node_query).data()]
            rel_types = [r['relationshipType'] for r in self.client.run(rel_query).data()]
            return {"node_types": node_types, "relationship_types": rel_types}
        except Exception as e:
            logger.error("schema_fetch_failed", error=str(e))
            return {"node_types": [], "relationship_types": []}

    def get_schema_summary(self) -> str:
        """获取 Schema 文本摘要，供 text2cypher prompt 使用"""
        schema = self.get_schema()
        node_types = schema.get("node_types", [])
        rel_types = schema.get("relationship_types", [])
        lines = [f"节点标签: {', '.join(node_types) if node_types else '无'}"]
        lines.append(f"关系类型: {', '.join(rel_types) if rel_types else '无'}")
        return "\n".join(lines)

    async def text_to_cypher(
        self, user_query: str, entities: Dict, intent_response: str = ""
    ) -> Tuple[Optional[str], Optional[List[Dict]]]:
        """Text2Cypher 入口：将自然语言转为 Cypher 查询并执行，返回 (prompt_segment, raw_results)"""
        from app.services.text2cypher_service import text2cypher_service as t2c
        return await t2c.execute_text2cypher(user_query, entities, intent_response)

    @staticmethod
    def validate_cypher(cypher: str) -> bool:
        """仅允许只读 Cypher 语句"""
        forbidden = ["CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE", "DROP"]
        upper = cypher.upper()
        return not any(kw in upper for kw in forbidden)

    # ── Search & autocomplete ───────────────────────────────────────

    def search_entities(self, query: str, limit: int = 20, offset: int = 0) -> dict:
        """模糊搜索实体 —— 跨所有节点类型，用于 Vue3 搜索框自动补全"""
        if self.client is None:
            return {"items": [], "total": 0}

        # Escape backslashes and double quotes inside the query for Cypher string literal
        safe_query = query.replace("\\", "\\\\").replace('"', '\\"')
        search_pattern = f"(?i).*{safe_query}.*"

        cypher = """
            CALL {
                MATCH (n:疾病) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '疾病' AS label, 'exact' AS match_type
                UNION ALL
                MATCH (n:药品) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '药品' AS label, 'exact' AS match_type
                UNION ALL
                MATCH (n:疾病症状) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '疾病症状' AS label, 'exact' AS match_type
                UNION ALL
                MATCH (n:食物) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '食物' AS label, 'exact' AS match_type
                UNION ALL
                MATCH (n:检查项目) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '检查项目' AS label, 'exact' AS match_type
                UNION ALL
                MATCH (n:科目) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '科目' AS label, 'exact' AS match_type
                UNION ALL
                MATCH (n:治疗方法) WHERE n.名称 =~ $pattern RETURN n.名称 AS name, '治疗方法' AS label, 'exact' AS match_type
            }
            RETURN name, label, match_type
            ORDER BY name
            SKIP $offset LIMIT $limit
        """

        # Also run a CONTAINS-based fuzzy search for broader results
        fuzzy_cypher = """
            CALL {
                MATCH (n:疾病) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '疾病' AS label, 'fuzzy' AS match_type
                UNION ALL
                MATCH (n:药品) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '药品' AS label, 'fuzzy' AS match_type
                UNION ALL
                MATCH (n:疾病症状) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '疾病症状' AS label, 'fuzzy' AS match_type
                UNION ALL
                MATCH (n:食物) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '食物' AS label, 'fuzzy' AS match_type
                UNION ALL
                MATCH (n:检查项目) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '检查项目' AS label, 'fuzzy' AS match_type
                UNION ALL
                MATCH (n:科目) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '科目' AS label, 'fuzzy' AS match_type
                UNION ALL
                MATCH (n:治疗方法) WHERE n.名称 CONTAINS $query RETURN n.名称 AS name, '治疗方法' AS label, 'fuzzy' AS match_type
            }
            RETURN name, label, match_type
            ORDER BY name
            SKIP $offset LIMIT $limit
        """

        try:
            # Prefer regex for short queries, CONTAINS for longer ones
            if len(query) <= 3:
                results = self.client.run(cypher, pattern=search_pattern, offset=offset, limit=limit).data()
            else:
                results = self.client.run(fuzzy_cypher, query=query, offset=offset, limit=limit).data()

            # Deduplicate by (name, label) — exact match takes priority
            seen = set()
            items = []
            for r in results:
                key = (r["name"], r["label"])
                if key not in seen:
                    seen.add(key)
                    items.append({"name": r["name"], "label": r["label"], "match_type": r["match_type"]})

            # Count total (simplified: count distinct names across all labels)
            total = len(items)

            return {"items": items, "total": total}
        except Exception as e:
            logger.error("entity_search_failed", error=str(e))
            return {"items": [], "total": 0}

    def fast_path_query(self, entity_name: str, relation_type: str) -> list:
        """快速路径查询：直接 1-hop Cypher，响应 < 1s"""
        if self.client is None:
            return []

        # Map relation types to Cypher patterns
        relation_map = {
            "疾病使用药品": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病使用药品]->(b:药品) RETURN b.名称 AS result, '药品' AS type",
                "label": "药品",
            },
            "疾病的症状": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病的症状]->(b:疾病症状) RETURN b.名称 AS result, '疾病症状' AS type",
                "label": "疾病症状",
            },
            "疾病宜吃食物": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病宜吃食物]->(b:食物) RETURN b.名称 AS result, '食物' AS type",
                "label": "食物",
            },
            "疾病忌吃食物": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病忌吃食物]->(b:食物) RETURN b.名称 AS result, '食物' AS type",
                "label": "食物",
            },
            "疾病所需检查": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病所需检查]->(b:检查项目) RETURN b.名称 AS result, '检查项目' AS type",
                "label": "检查项目",
            },
            "疾病所属科目": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病所属科目]->(b:科目) RETURN b.名称 AS result, '科目' AS type",
                "label": "科目",
            },
            "治疗的方法": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:治疗的方法]->(b:治疗方法) RETURN b.名称 AS result, '治疗方法' AS type",
                "label": "治疗方法",
            },
            "疾病并发疾病": {
                "cypher": "MATCH (a:疾病{名称:$name})-[r:疾病并发疾病]->(b:疾病) RETURN b.名称 AS result, '疾病' AS type",
                "label": "疾病",
            },
            "疾病简介": {
                "cypher": "MATCH (a:疾病{名称:$name}) RETURN a.疾病简介 AS result, '属性' AS type",
                "label": None,
            },
            "疾病病因": {
                "cypher": "MATCH (a:疾病{名称:$name}) RETURN a.疾病病因 AS result, '属性' AS type",
                "label": None,
            },
            "预防措施": {
                "cypher": "MATCH (a:疾病{名称:$name}) RETURN a.预防措施 AS result, '属性' AS type",
                "label": None,
            },
            "治疗周期": {
                "cypher": "MATCH (a:疾病{名称:$name}) RETURN a.治疗周期 AS result, '属性' AS type",
                "label": None,
            },
            "治愈概率": {
                "cypher": "MATCH (a:疾病{名称:$name}) RETURN a.治愈概率 AS result, '属性' AS type",
                "label": None,
            },
            "疾病易感人群": {
                "cypher": "MATCH (a:疾病{名称:$name}) RETURN a.疾病易感人群 AS result, '属性' AS type",
                "label": None,
            },
            # Reverse lookup: symptom → diseases
            "症状反查疾病": {
                "cypher": "MATCH (a:疾病)-[r:疾病的症状]->(b:疾病症状{名称:$name}) RETURN a.名称 AS result, '疾病' AS type",
                "label": "疾病",
            },
        }

        entry = relation_map.get(relation_type)
        if not entry:
            return []

        try:
            results = self.client.run(entry["cypher"], name=entity_name).data()
            return [
                {"result": r.get("result"), "type": r.get("type"), "relationship": relation_type}
                for r in results
                if r.get("result")
            ]
        except Exception as e:
            logger.error("fast_path_query_failed", error=str(e), entity=entity_name, relation=relation_type)
            return []

    def count_nodes(self, label: str, name_filter: str = None) -> int:
        """统计节点数量，用于分页"""
        if self.client is None:
            return 0
        try:
            if name_filter:
                safe = name_filter.replace("\\", "\\\\").replace('"', '\\"')
                cypher = f'MATCH (n:{label}) WHERE n.名称 CONTAINS $filter RETURN count(n) AS cnt'
                result = self.client.run(cypher, filter=name_filter).data()
            else:
                cypher = f"MATCH (n:{label}) RETURN count(n) AS cnt"
                result = self.client.run(cypher).data()
            return result[0]["cnt"] if result else 0
        except Exception as e:
            logger.error("count_nodes_failed", error=str(e), label=label)
            return 0


kg_service = KGService()
