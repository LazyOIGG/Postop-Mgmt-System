import py2neo
import random
from typing import Dict, List, Optional
from app.core.config import settings

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
            print("[SUCCESS] Neo4j连接成功")
        except Exception as e:
            print(f"[ERROR] Neo4j连接失败: {e}")
            self.client = None

    def add_shuxing_prompt(self, entity, shuxing):
        """查询疾病属性并生成提示"""
        if self.client is None: return ""
        try:
            sql_q = "match (a:疾病{名称:'%s'}) return a.%s" % (entity, shuxing)
            res = self.client.run(sql_q).data()
            if res:
                content = "".join(res[0].values())
                return f"<提示>用户对{entity}有查询{shuxing}需求，知识库内容：{content}</提示>"
        except Exception as e:
            print(f"[WARN] 属性查询失败({shuxing}): {e}")
        return ""

    def add_lianxi_prompt(self, entity, lianxi, target):
        """查询疾病联系并生成提示"""
        if self.client is None: return ""
        try:
            sql_q = "match (a:疾病{名称:'%s'})-[r:%s]->(b:%s) return b.名称" % (entity, lianxi, target)
            res = self.client.run(sql_q).data()
            if res:
                names = "、".join([list(data.values())[0] for data in res])
                return f"<提示>用户对{entity}有查询{lianxi}需求，知识库内容：{names}</提示>"
        except Exception as e:
            print(f"[WARN] 关系查询失败({lianxi}): {e}")
        return ""

    def generate_enhanced_prompt(self, intent_response: str, query: str, entities: Dict) -> tuple:
        """根据意图和实体生成增强 Prompt"""
        neo4j_prompt = '<指令>你是一个专业的术后管理助手。回答必须严格基于给定的提示内容，不可自由发挥。如无信息，请回答“根据已知信息无法回答该问题”。</指令>'
        has_kg = False
        
        # 症状推测逻辑
        if '疾病症状' in entities and '疾病' not in entities and self.client:
            try:
                sql_q = "match (a:疾病)-[r:疾病的症状]->(b:疾病症状 {名称:'%s'}) return a.名称" % (entities['疾病症状'])
                res = [v for d in self.client.run(sql_q).data() for v in d.values()]
                if res:
                    has_kg = True
                    entities['疾病'] = random.choice(res)
                    neo4j_prompt += f"<提示>基于{entities['疾病症状']}，推测可能是：{'、'.join(res)}。请告知用户这仅为推测。</提示>"
            except Exception as e:
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

        # 最终 Prompt 构造
        if has_kg:
            prompt = f"{neo4j_prompt}\n<用户问题>{query}</用户问题>\n<注意>请将提示知识整理成结构清晰、专业的回答，并在末尾标注“(本回答基于知识图谱生成)”。</注意>"
        else:
            prompt = f"<指令>你是一个术后管理机器人。请直接回答用户问题，并确保准确专业。</指令>\n<用户问题>{query}</用户问题>\n<注意>末尾请标注“(本回答由大语言模型生成)”。</注意>"
        
        return prompt, "、".join(yitu_list), entities, has_kg

    def query(self, cypher_query: str):
        """执行原生 Cypher 查询"""
        if self.client is None: return []
        try:
            return self.client.run(cypher_query).data()
        except Exception as e:
            print(f"[ERROR] 图谱查询失败: {e}")
            return []

kg_service = KGService()
