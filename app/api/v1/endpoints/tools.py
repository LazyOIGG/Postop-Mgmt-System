from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Optional
from app.core.security import get_current_user
from app.services.ner_service import ner_service
from app.services.intent_service import intent_service

router = APIRouter()

@router.post("/entity-recognition")
async def tool_entity_recognition(query: str, user: Dict = Depends(get_current_user)):
    """实体识别工具"""
    try:
        entities = ner_service.recognize(query)
        return {
            "success": True,
            "query": query,
            "entities": entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实体识别失败: {str(e)}")

@router.post("/intent-recognition")
async def tool_intent_recognition(query: str, model_choice: Optional[str] = None,
                                  user: Dict = Depends(get_current_user)):
    """意图识别工具"""
    try:
        intent_result = await intent_service.recognize(query, model_choice)
        return {
            "success": True,
            "query": query,
            "intent_result": intent_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"意图识别失败: {str(e)}")
