from fastapi import APIRouter, Depends, UploadFile, File
from app.core.security import get_current_user
from app.services.speech_service import speech_service
from app.services.image_service import image_service
from typing import Dict

router = APIRouter()

@router.post("/speech/stt")
async def speech_to_text(file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    """语音识别 (未来功能)"""
    content = await file.read()
    result = await speech_service.transcribe(content)
    return {"success": True, "text": result}

@router.post("/image/analyze")
async def analyze_image(file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    """图像识别 (未来功能)"""
    content = await file.read()
    result = await image_service.analyze_medical_image(content)
    return {"success": True, "analysis": result}

@router.post("/image/ocr")
async def image_ocr(file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    """医疗报告文字提取 (未来功能)"""
    content = await file.read()
    result = await image_service.extract_text_from_report(content)
    return {"success": True, "text": result}
