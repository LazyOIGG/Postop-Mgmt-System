from fastapi import APIRouter, Depends, UploadFile, File, Form
from app.core.security import get_current_user
from app.services.health_assessment_service import health_assessment_service
from app.services.speech_service import speech_service
from app.services.image_service import image_service
from app.db.session import db_instance
from typing import Dict, Optional
import json

router = APIRouter()

@router.post("/text")
async def assess_text(
    text: str = Form(...),
    user: Dict = Depends(get_current_user)
):
    """文字输入健康评估"""
    result = await health_assessment_service.assess(text, "text")
    
    # 保存评估结果到数据库
    db_instance.save_health_assessment(
        username=user["username"],
        source_type="text",
        input_text=text,
        risk_level=result["risk_level"],
        risk_reasons=json.dumps(result["risk_reasons"], ensure_ascii=False),
        need_hospital=result["need_hospital"],
        advice=result["advice"]
    )
    
    return {
        "success": True,
        "result": result
    }

@router.post("/speech")
async def assess_speech(
    file: UploadFile = File(...),
    user: Dict = Depends(get_current_user)
):
    """语音输入健康评估"""
    content = await file.read()
    recognized_text = await speech_service.transcribe(content)
    
    if recognized_text.startswith("语音识别失败"):
        return {
            "success": False,
            "detail": recognized_text
        }
    
    result = await health_assessment_service.assess(recognized_text, "speech")
    
    # 保存评估结果到数据库
    db_instance.save_health_assessment(
        username=user["username"],
        source_type="speech",
        input_text=recognized_text,
        risk_level=result["risk_level"],
        risk_reasons=json.dumps(result["risk_reasons"], ensure_ascii=False),
        need_hospital=result["need_hospital"],
        advice=result["advice"]
    )
    
    return {
        "success": True,
        "recognized_text": recognized_text,
        "result": result
    }

@router.post("/image")
async def assess_image(
    file: UploadFile = File(...),
    user: Dict = Depends(get_current_user)
):
    """图片/PDF输入健康评估"""
    content = await file.read()
    
    ocr_result = await image_service.extract_text_from_report(
        image_data=content,
        filename=file.filename,
        content_type=file.content_type
    )
    
    if not ocr_result or ocr_result.get("message"):
        return {
            "success": False,
            "detail": ocr_result.get("message", "OCR识别失败")
        }
    
    ocr_text = ocr_result.get("text", "")
    result = await health_assessment_service.assess(ocr_text, "image")
    
    # 保存评估结果到数据库
    db_instance.save_health_assessment(
        username=user["username"],
        source_type="image",
        input_text=ocr_text,
        risk_level=result["risk_level"],
        risk_reasons=json.dumps(result["risk_reasons"], ensure_ascii=False),
        need_hospital=result["need_hospital"],
        advice=result["advice"]
    )
    
    return {
        "success": True,
        "ocr_text": ocr_text,
        "result": result
    }

@router.get("/history")
async def get_assessment_history(
    limit: int = 20,
    offset: int = 0,
    user: Dict = Depends(get_current_user)
):
    """获取健康评估历史记录"""
    history = db_instance.get_health_assessment_history(
        username=user["username"],
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "history": history
    }
