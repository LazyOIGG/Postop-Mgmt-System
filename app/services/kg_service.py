import py2neo
import random
import re
from typing import Dict, List, Optional, Tuple
from app.core.config import settings
from app.services.llm_service import llm_service


class KGService:
    """知识图谱服务（P3.13 增强版）"""

    def __init__(self):
        try:
            self.client = py2neo.Graph(
                settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
                name=settings.NEO4J_NAME
            )
            print("[SUCCESS] Neo4j连接成功")
        except Exception as e:
            print(f"[ERROR] Neo4j连接失败: {e}")
            self.client = None

    def _sanitize_cypher(self, cypher: str) -> bool:
        """检查 Cypher 查询是否只包含只读操作，拦截写入/删除"""
        upper = cypher.upper().strip()
        dangerous = ['CREATE', 'DELETE', 'DROP', 'SET', 'REMOVE', 'MERGE', 'DETACH']
        for kw in dangerous:
            # 仅允许前导空白后的关键字（避免匹配到 MATCH ... CREATE 的情况）
            if re.search(rf'\b{kw}\b', upper):
                return False
        return upper.startswith('MATCH') or upper.startswith('CALL')

    def add_shuxing_prompt(self, entity: str, shuxing: str) -> str:
        if self.client is None:
            return ""
        try:
            res = self.client.run(
                "MATCH (a:疾病{名称: $name}) RETURN a[$prop] AS val",
                name=entity, prop=shuxing
            ).data()
            if res and res[0].get('val'):
                content = str(res[0]['val'])
                return f"<提示>用户对{entity}有查询{shuxing}需求，知识库内容：{content}</提示>"
        except py2neo.errors.ClientError as e:
            print(f"[WARN] 属性查询失败({shuxing}): {e}")
        return ""

    def add_lianxi_prompt(self, entity: str, lianxi: str, target: str) -> str:
        if self.client is None:
            return ""
        try:
            res = self.client.run(
                f"MATCH (a:疾病{{名称:$name}})-[r:{lianxi}]->(b:{target}) RETURN b.名称 AS name",
                name=entity
            ).data()
            if res:
                names = "、".join([d['name'] for d in res if d.get('name')])
                return f"<提示>用户对{entity}有查询{lianxi}需求，知识库内容：{names}</提示>"
        except py2neo.errors.ClientError as e:
            print(f"[WARN] 关系查询失败({lianxi}): {e}")
        return ""

    # ── P3.13 新增方法 ──

    async def text_to_cypher(self, query: str) -> Optional[str]:
        """使用 LLM 将自然语言查询转为 Cypher"""
        prompt = f"""你是一个医疗知识图谱 Cypher 查询生成器。图谱结构：
- 节点类型：疾病、药品、食物、检查项目、科目、疾病症状、治疗方法、药品商
- 关系类型：疾病的症状、疾病使用药品、疾病宜吃食物、疾病忌吃食物、疾病所需检查、
           疾病所属科目、治疗的方法、疾病并发疾病、生产、药物相互作用、术后并发症、药物禁忌
- 查询疾病属性：MATCH (a:疾病{{名称:$name}}) RETURN a.疾病简介, a.疾病病因, ...

请将以下用户问题转为 Cypher 查询（仅返回 Cypher 语句，不要其他内容）：

用户问题：{query}

要求：
1. 仅生成只读 MATCH 查询
2. 使用参数化占位符 $name, $keyword 代替用户输入
3. 如果无法转为查询，返回 NONE"""
        try:
            result = await llm_service.generate_completion_with_messages(
                messages=[{"role": "user", "content": prompt}]
            )
            cypher = result.strip()
            if cypher.upper() == "NONE":
                return None
            # 去掉可能的 markdown 代码块标记
            cypher = re.sub(r'^```(?:cypher)?\n?', '', cypher)
            cypher = re.sub(r'\n?```$', '', cypher)
            return cypher
        except Exception as e:
            print(f"[ERROR] text_to_cypher 失败: {e}")
            return None

    def multi_hop_query(self, entity_name: str, max_hops: int = None) -> List[Dict]:
        """多跳查询 — 获取指定疾病节点周围的多跳子图"""
        if self.client is None:
            return []
        hops = max_hops or settings.KG_MAX_HOPS
        try:
            cypher = f"""
                MATCH path = (a:疾病{{名称:$name}})-[*1..{hops}]-(b)
                RETURN nodes(path) AS nodes, relationships(path) AS rels
                LIMIT {settings.KG_VISUALIZE_MAX_NODES}
            """
            result = self.client.run(cypher, name=entity_name).data()
            nodes_set = {}
            edges = []
            for record in result:
                for node in record.get('nodes', []):
                    node_id = node.identity
                    if node_id not in nodes_set:
                        labels = list(node.labels)
                        props = dict(node)
                        name = props.get('名称', str(node_id))
                        nodes_set[node_id] = {
                            'id': node_id,
                            'name': name,
                            'labels': labels,
                            'properties': {k: v for k, v in props.items() if k != '名称'}
                        }
                for rel in record.get('rels', []):
                    edges.append({
                        'source': rel.start_node.identity,
                        'target': rel.end_node.identity,
                        'type': type(rel).__name__
                    })
            return [{'nodes': list(nodes_set.values()), 'edges': edges}]
        except py2neo.errors.ClientError as e:
            print(f"[ERROR] 多跳查询失败: {e}")
            return []

    def get_schema(self) -> Dict:
        """获取知识图谱 schema"""
        if self.client is None:
            return {'node_types': [], 'relationship_types': []}
        try:
            node_types = []
            label_result = self.client.run("CALL db.labels()").data()
            for rec in label_result:
                label = rec.get('label', '')
                count_result = self.client.run(
                    f"MATCH (n:`{label}`) RETURN count(n) AS cnt"
                ).data()
                node_types.append({
                    'label': label,
                    'count': count_result[0]['cnt'] if count_result else 0
                })

            rel_result = self.client.run("CALL db.relationshipTypes()").data()
            relationship_types = [r.get('relationshipType', '') for r in rel_result]

            return {'node_types': node_types, 'relationship_types': relationship_types}
        except py2neo.errors.ClientError as e:
            print(f"[ERROR] 获取 schema 失败: {e}")
            return {'node_types': [], 'relationship_types': []}

    def generate_enhanced_prompt(self, intent_response: str, query: str, entities: Dict) -> Tuple[str, str, Dict, bool]:
        """根据意图和实体生成增强 Prompt（P3.13 升级版）"""
        neo4j_prompt = '<指令>你是一个专业的术后管理助手。回答必须严格基于给定的提示内容，不可自由发挥。如无信息，请回答"根据已知信息无法回答该问题"。</指令>'
        has_kg = False

        # 症状推测逻辑（修复注入）
        if '疾病症状' in entities and '疾病' not in entities and self.client:
            try:
                res = self.client.run(
                    "MATCH (a:疾病)-[r:疾病的症状]->(b:疾病症状{名称:$name}) RETURN a.名称 AS name",
                    name=entities['疾病症状']
                ).data()
                names = [d['name'] for d in res if d.get('name')]
                if names:
                    has_kg = True
                    entities['疾病'] = random.choice(names)
                    neo4j_prompt += f"<提示>基于{entities['疾病症状']}，推测可能是：{'、'.join(names)}。请告知用户这仅为推测。</提示>"
            except py2neo.errors.ClientError as e:
                print(f"[ERROR] 症状推测失败: {e}")

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

        if has_kg:
            prompt = f"{neo4j_prompt}\n<用户问题>{query}</用户问题>\n<注意>请将提示知识整理成结构清晰、专业的回答，并在末尾标注\"(本回答基于知识图谱生成)\"。</注意>"
        else:
            prompt = f"<指令>你是一个术后管理机器人。请直接回答用户问题，并确保准确专业。</指令>\n<用户问题>{query}</用户问题>\n<注意>末尾请标注\"(本回答由大语言模型生成)\"。</注意>"

        return prompt, "、".join(yitu_list), entities, has_kg

    def query(self, cypher_query: str, params: Dict = None) -> List[Dict]:
        """执行原生 Cypher 查询（仅允许只读）"""
        if self.client is None:
            return []
        if not self._sanitize_cypher(cypher_query):
            print(f"[SECURITY] 拦截了危险 Cypher 查询: {cypher_query[:100]}")
            return []
        try:
            return self.client.run(cypher_query, **(params or {})).data()
        except py2neo.errors.ClientError as e:
            print(f"[ERROR] 图谱查询失败: {e}")
            return []


kg_service = KGService()
