import re
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.response import ApiResponse
from app.core.security import get_current_user
from app.models.schemas import KnowledgeGraphQuery, VisualizeRequest
from app.services.kg_service import kg_service

router = APIRouter()

# ── Security: forbidden patterns ───────────────────────────────────

FORBIDDEN_KEYWORDS = ["CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE", "DROP",
                      "ALTER", "TRUNCATE", "INSERT", "UPDATE", "GRANT", "REVOKE"]

# Patterns that indicate SQL/Cypher injection attempts
INJECTION_PATTERNS = [
    # Comment injection
    (r'--', "SQL注释符"),
    (r'//', "代码注释符"),
    (r'/\*', "块注释开始"),
    (r'\*/', "块注释结束"),
    # Statement chaining
    (r';\s*(DROP|DELETE|CREATE|ALTER|TRUNCATE|INSERT|UPDATE|GRANT|REVOKE|MERGE|SET|DETACH)',
     "语句链接+危险操作"),
    # Union injection
    (r'\bUNION\s+SELECT\b', "UNION注入"),
    # System commands
    (r'\bEXEC\b.*\b(sp_|xp_)', "系统存储过程"),
    # SQL injection with quotes: ' OR '1'='1, ' AND 'x'='x, etc.
    (r"'[\s]*\b(OR|AND)\b[\s]*'[^']*'[\s]*=", "SQL引号注入(OR/AND)"),
    # String concatenation injection
    (r"'[\s]*\|\|[\s]*'", "SQL字符串拼接注入"),
    # Hex-encoded injection
    (r'\b0x[0-9a-fA-F]{8,}', "十六进制编码注入"),
    # Suspicious function calls
    (r'\b(?:sleep|benchmark|load_file|into\s+(?:outfile|dumpfile))\s*\(', "危险函数调用"),
    # Boolean-based blind injection patterns
    (r"\b(?:OR|AND)\b[\s]+\d+[\s]*=[\s]*\d+", "布尔盲注"),
]

# ── Fast path: pattern → relation mapping ──────────────────────────

FAST_PATH_PATTERNS = [
    # (regex pattern, relation_type, extract_entity_group)
    (r'(.+?)(?:用什么药|吃什么药|开什么药|的药品|药品)', "疾病使用药品", 1),
    (r'(.+?)(?:有什么症状|什么症状|的症状|症状|表现|会怎么样)', "疾病的症状", 1),
    (r'(.+?)(?:什么原因|病因|为什么会得|的原因|为什么会)', "疾病病因", 1),
    (r'(.+?)(?:怎么预防|预防|如何预防)', "预防措施", 1),
    (r'(.+?)(?:怎么治疗|治疗方法|怎么治|如何治疗|治疗)', "治疗的方法", 1),
    (r'(.+?)(?:吃什么|宜吃|饮食|能吃|可以吃)', "疾病宜吃食物", 1),
    (r'(.+?)(?:不能吃|忌吃|忌口|不能|不要吃)', "疾病忌吃食物", 1),
    (r'(.+?)(?:做什么检查|检查项目|查什么|检查)', "疾病所需检查", 1),
    (r'(.+?)(?:挂什么科|看什么科|科室|什么科)', "疾病所属科目", 1),
    (r'(.+?)(?:治疗周期|多久能好|多长时间)', "治疗周期", 1),
    (r'(.+?)(?:治愈概率|治愈率|能不能治好)', "治愈概率", 1),
    (r'(.+?)(?:易感人群|什么人容易|高发人群)', "疾病易感人群", 1),
    (r'(.+?)(?:会并发|并发症|并发疾病)', "疾病并发疾病", 1),
    # Reverse: symptom → disease
    (r'(.+?)(?:是什么病|可能是.*病|是什么疾病)', "症状反查疾病", 1),
]

# Question words that suggest NL query needing text2cypher
NL_QUESTION_MARKERS = ["什么", "怎么", "如何", "为什么", "吗", "？", "?", "吃了", "服用",
                       "加重", "缓解", "好转", "恶化", "怎么办", "会不会", "能不能"]


# ── Security helpers ───────────────────────────────────────────────

def _sanitize_search_input(q: str) -> Tuple[bool, str]:
    """安全过滤搜索输入，返回 (is_safe, reason)"""
    if not q or not q.strip():
        return True, ""

    stripped = q.strip()

    # 1. Check for injection patterns
    for pattern, desc in INJECTION_PATTERNS:
        if re.search(pattern, stripped, re.IGNORECASE):
            return False, f"查询包含不安全内容，已被安全过滤器拦截"

    # 2. Check if query starts with a forbidden keyword (as a command)
    first_word = stripped.split()[0].upper() if stripped.split() else ""
    if first_word in FORBIDDEN_KEYWORDS:
        return False, f"查询包含不安全内容，已被安全过滤器拦截"

    # 3. Check for unbalanced single quotes (SQL string escape)
    # Allow Chinese quote marks '' and "" but block ASCII single quotes used for injection
    single_quote_count = stripped.count("'")
    if single_quote_count > 0 and single_quote_count % 2 != 0:
        return False, f"查询包含不安全内容，已被安全过滤器拦截"

    # 4. Block standalone semicolons (statement terminators)
    if ';' in stripped:
        return False, f"查询包含不安全内容，已被安全过滤器拦截"

    return True, ""


# ── Fast path helpers ──────────────────────────────────────────────

def _extract_entity_from_query(query: str) -> Optional[str]:
    """从查询中提取可能的实体名称（用于 Neo4j 查找）"""
    # Try to find the longest entity candidate by stripping known question words
    cleaned = query.strip()
    # Remove trailing question words
    for marker in ["用什么药", "吃什么药", "的症状", "怎么治疗", "怎么预防",
                    "是什么病", "做什么检查", "挂什么科", "治疗周期",
                    "治愈概率", "易感人群", "并发疾病", "什么原因",
                    "吃什么", "不能吃", "？", "?"]:
        if marker in cleaned:
            # Return the part before the first marker
            idx = cleaned.index(marker)
            if idx > 0:
                return cleaned[:idx]
    # If no markers found but query is short, it might be a plain entity name
    if len(cleaned) <= 20 and not any(m in cleaned for m in NL_QUESTION_MARKERS):
        return cleaned
    return None


def _detect_fast_path_pattern(query: str) -> Optional[Tuple[str, str]]:
    """检测查询是否匹配快速路径模式，返回 (entity_name, relation_type) 或 None"""
    for pattern, relation_type, group_idx in FAST_PATH_PATTERNS:
        match = re.match(pattern, query)
        if match:
            entity_name = match.group(group_idx).strip()
            if entity_name and len(entity_name) >= 1 and len(entity_name) <= 30:
                return entity_name, relation_type
    return None


def _is_nl_question(query: str) -> bool:
    """判断是否是自然语言问题（需要 text2cypher）"""
    if len(query) >= 15:
        return True
    if any(marker in query for marker in NL_QUESTION_MARKERS):
        return True
    # Multiple entities likely (spaces between Chinese words suggest multiple concepts)
    if len(query) >= 8 and ('了' in query or '的' in query):
        return True
    return False


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/search")
async def kg_search(
    q: str = Query(..., description="搜索关键词或自然语言问题"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user: Dict = Depends(get_current_user),
):
    """知识图谱搜索 —— 支持实体模糊搜索（自动补全）和自然语言查询（Text2Cypher）

    - 简单实体名如"感冒" → 模糊匹配所有节点类型
    - 模式查询如"感冒用什么药" → 快速路径直接 Cypher（< 1s）
    - 复杂 NL 如"吃了阿莫西林后头痛加重" → Text2Cypher 多跳查询
    - 注入攻击如"'; DROP TABLE; //" → 安全过滤器拦截
    """
    # ── 1. Security sanitization ──
    is_safe, reason = _sanitize_search_input(q)
    if not is_safe:
        raise HTTPException(status_code=400, detail=reason)

    if kg_service.client is None:
        return {
            "success": True,
            "query": q,
            "source": "none",
            "entities": [],
            "results": [],
            "graph": None,
            "count": 0,
            "message": "Neo4j连接不可用",
        }

    offset = (page - 1) * page_size
    response_data = {
        "success": True,
        "query": q,
        "source": "fast_path",
        "entities": [],
        "results": [],
        "graph": None,
        "count": 0,
    }

    # ── 2. Always run entity fuzzy search (for autocomplete) ──
    entity_result = kg_service.search_entities(q, limit=page_size, offset=offset)
    response_data["entities"] = entity_result.get("items", [])

    # ── 3. Try fast-path pattern matching ──
    fast_match = _detect_fast_path_pattern(q)
    if fast_match:
        entity_name, relation_type = fast_match
        fast_results = kg_service.fast_path_query(entity_name, relation_type)
        if fast_results:
            response_data["source"] = "fast_path"
            response_data["results"] = fast_results
            response_data["count"] = len(fast_results)
            response_data["intent"] = relation_type
            response_data["entity"] = entity_name

            # Get subgraph for visualization
            graph_data = kg_service.multi_hop_query(entity_name, max_hops=2)
            response_data["graph"] = graph_data if graph_data else {"nodes": [], "edges": []}
            return response_data

    # ── 4. If no fast-path match but query looks like an entity, try direct entity lookup ──
    extracted_entity = _extract_entity_from_query(q)
    if extracted_entity and extracted_entity != q:
        fast_match2 = _detect_fast_path_pattern(extracted_entity)
        if not fast_match2:
            # Try looking up as a plain entity
            entity_search = kg_service.search_entities(extracted_entity, limit=5, offset=0)
            if entity_search.get("items"):
                response_data["entities"] = entity_search["items"]
                response_data["entity"] = extracted_entity
                # Try to get subgraph for the first exact match
                first_entity = entity_search["items"][0]
                graph_data = kg_service.multi_hop_query(first_entity["name"], max_hops=2)
                response_data["graph"] = graph_data if graph_data else {"nodes": [], "edges": []}

    # ── 5. Text2Cypher fallback for complex NL queries ──
    if _is_nl_question(q) and settings.KG_TEXT2CYPHER_ENABLED:
        try:
            from app.services.text2cypher_service import text2cypher_service as t2c

            # Use NER service for entity extraction if available
            entities = {}
            try:
                from app.services.ner_service import ner_service
                entities = ner_service.recognize(q)
            except Exception:
                pass

            t2c_prompt, t2c_results = await t2c.execute_text2cypher(q, entities, "")
            if t2c_prompt and t2c_results:
                response_data["source"] = "text2cypher"
                response_data["results"] = t2c_results
                response_data["count"] = len(t2c_results)
                response_data["cypher"] = t2c_prompt[:500]  # truncated for display

                # Build subgraph from text2cypher results
                graph_nodes = {}
                graph_edges = []
                for record in t2c_results:
                    for key, value in record.items():
                        if value is not None and isinstance(value, str) and len(value) < 100:
                            graph_nodes[value] = {"id": value, "name": value, "labels": [key]}

                if graph_nodes:
                    # Try multi-hop on the most relevant entity
                    primary_entity = None
                    for entity_key in ["疾病", "药品", "疾病症状"]:
                        if entity_key in entities:
                            primary_entity = entities[entity_key]
                            break
                    if not primary_entity and extracted_entity:
                        primary_entity = extracted_entity

                    if primary_entity:
                        graph_data = kg_service.multi_hop_query(primary_entity, max_hops=2)
                        response_data["graph"] = graph_data if graph_data else {"nodes": list(graph_nodes.values()), "edges": graph_edges}
                    else:
                        response_data["graph"] = {"nodes": list(graph_nodes.values()), "edges": graph_edges}
                else:
                    response_data["graph"] = {"nodes": [], "edges": []}
        except Exception:
            # text2cypher failed silently — fast_path results still returned
            pass

    return response_data


@router.get("/diseases")
async def get_diseases(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    user: Dict = Depends(get_current_user),
):
    """获取疾病列表（分页）"""
    if kg_service.client is None:
        return ApiResponse.ok(
            data={"diseases": []},
            message="Neo4j不可用"
        )

    try:
        offset = (page - 1) * page_size
        total = kg_service.count_nodes("疾病")
        query = "MATCH (n:疾病) RETURN n.名称 as name ORDER BY name SKIP $offset LIMIT $limit"
        results = kg_service.client.run(query, offset=offset, limit=page_size).data()
        diseases = [r['name'] for r in results if 'name' in r]

        return ApiResponse.paginated(
            items=diseases,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        return ApiResponse.fail(message=f"获取失败: {str(e)}")


@router.post("/query")
async def kg_query(request: KnowledgeGraphQuery, user: Dict = Depends(get_current_user)):
    """查询知识图谱"""
    try:
        if kg_service.client is None:
            raise HTTPException(status_code=500, detail="Neo4j连接不可用")

        results = kg_service.query(request.cypher_query)
        return {
            "success": True,
            "query": request.cypher_query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/visualize")
async def kg_visualize(request: VisualizeRequest, user: Dict = Depends(get_current_user)):
    """获取知识图谱子图用于前端可视化"""
    try:
        if kg_service.client is None:
            raise HTTPException(status_code=500, detail="Neo4j连接不可用")

        result = kg_service.multi_hop_query(request.entity_name, request.max_hops)
        return {
            "success": True,
            "entity": request.entity_name,
            "data": result if result else {"nodes": [], "edges": []}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"可视化查询失败: {str(e)}")


@router.get("/schema")
async def kg_schema(user: Dict = Depends(get_current_user)):
    """获取知识图谱 Schema（节点类型和关系类型）"""
    try:
        if kg_service.client is None:
            raise HTTPException(status_code=500, detail="Neo4j连接不可用")

        schema = kg_service.get_schema()
        return {
            "success": True,
            **schema
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Schema失败: {str(e)}")
