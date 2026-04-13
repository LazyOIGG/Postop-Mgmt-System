from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from app.models.schemas import KnowledgeGraphQuery
from app.core.security import get_current_user
from app.services.kg_service import kg_service

router = APIRouter()

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

@router.get("/diseases")
async def get_diseases(user: Dict = Depends(get_current_user)):
    """获取所有疾病列表"""
    try:
        if kg_service.client is None:
            return {
                "success": True,
                "diseases": [],
                "count": 0,
                "message": "Neo4j不可用"
            }

        query = "MATCH (n:疾病) RETURN n.名称 as name LIMIT 100"
        results = kg_service.query(query)
        diseases = [r['name'] for r in results if 'name' in r]

        return {
            "success": True,
            "diseases": diseases,
            "count": len(diseases)
        }
    except Exception as e:
        return {
            "success": False,
            "diseases": [],
            "count": 0,
            "message": f"获取失败: {str(e)}"
        }
