from .base import Tool
from .registry import tool_registry

# ── Tool schemas ──────────────────────────────────────────────────

QUERY_DRUG_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "drug_name": {
            "type": "string",
            "description": "药品名称"
        }
    },
    "required": ["drug_name"]
}

QUERY_DISEASE_SYMPTOMS_SCHEMA = {
    "type": "object",
    "properties": {
        "disease_name": {
            "type": "string",
            "description": "疾病名称"
        }
    },
    "required": ["disease_name"]
}

# ── Tool handlers ─────────────────────────────────────────────────

async def _query_drug_info(drug_name: str) -> str:
    try:
        from app.services.kg_service import kg_service
        result = kg_service.query(f"match (a:药品{{名称:'{drug_name}'}}) return a")
        if result:
            data = result[0]
            props = {k: v for k, v in data.get('a', {}).items() if v}
            if props:
                lines = [f"药品「{drug_name}」信息："]
                for k, v in props.items():
                    lines.append(f"  {k}: {v}")
                return "\n".join(lines)
    except Exception:
        pass
    return f"暂未在知识库中找到药品「{drug_name}」的详细信息。建议咨询医生或药师获取准确的用药指导。"


async def _query_disease_symptoms(disease_name: str) -> str:
    try:
        from app.services.kg_service import kg_service
        # Query disease basic info
        result = kg_service.query(f"match (a:疾病{{名称:'{disease_name}'}}) return a")
        if result:
            data = result[0]
            props = {k: v for k, v in data.get('a', {}).items() if v}
            if props:
                lines = [f"疾病「{disease_name}」信息："]
                for k, v in props.items():
                    lines.append(f"  {k}: {v}")
                return "\n".join(lines)
        # Try symptom relation
        result = kg_service.query(
            f"match (a:疾病{{名称:'{disease_name}'}})-[r:疾病的症状]->(b) return b.名称"
        )
        if result:
            symptoms = [list(d.values())[0] for d in result if d]
            if symptoms:
                return f"疾病「{disease_name}」相关症状：{'、'.join(symptoms)}"
    except Exception:
        pass
    return f"暂未在知识库中找到疾病「{disease_name}」的详细信息。建议咨询医生获取专业诊断。"


# ── Register tools ────────────────────────────────────────────────

query_drug_info_tool = Tool(
    name="query_drug_info",
    description="查询药品信息（适应症、用法用量、不良反应等）。当用户询问某药品信息时使用。",
    parameters=QUERY_DRUG_INFO_SCHEMA,
    handler=_query_drug_info
)

query_disease_symptoms_tool = Tool(
    name="query_disease_symptoms",
    description="查询疾病相关症状信息。当用户询问某疾病的症状、注意事项时使用。",
    parameters=QUERY_DISEASE_SYMPTOMS_SCHEMA,
    handler=_query_disease_symptoms
)

tool_registry.register(query_drug_info_tool)
tool_registry.register(query_disease_symptoms_tool)
