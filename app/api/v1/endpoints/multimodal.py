from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import Response
from app.core.security import get_current_user
from app.services.speech_service import speech_service
from app.services.image_service import image_service
from app.agents.orchestrator import orchestrator
from app.db.session import db_instance
from app.models.schemas import TTSRequest
from typing import Dict
import json

router = APIRouter()

@router.post("/image/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    user: Dict = Depends(get_current_user)
):
    content = await file.read()
    result = await image_service.analyze_medical_image(
        image_data=content,
        filename=file.filename,
        content_type=file.content_type
    )
    return {"success": True, "analysis": result}

@router.post("/image/ocr")
async def image_ocr(
    file: UploadFile = File(...),
    auto_answer: bool = Form(True),
    session_id: int | None = Form(None),
    user: Dict = Depends(get_current_user)
):
    """
    上传病例图片/PDF -> OCR -> 自动生成康复建议
    """
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

    response = {
        "success": True,
        "filename": file.filename,
        "ocr_text": ocr_result.get("text", ""),
        "avg_score": ocr_result.get("avg_score", 0.0),
        "structured": ocr_result.get("structured", {}),
        "details": ocr_result.get("details", []),
    }

    if auto_answer and ocr_result.get("text", "").strip():
        prompt_text = (
            "以下是患者上传的病例/检查报告OCR识别结果，请完成：\n"
            "1. 提炼关键信息\n"
            "2. 判断是否存在健康风险点\n"
            "3. 给出通俗易懂的健康建议\n"
            "4. 如有异常，提示尽快联系医生\n\n"
            f"OCR文本如下：\n{ocr_result['text']}"
        )

        chat_response = await orchestrator.process(prompt_text, user["username"])

        response["answer"] = chat_response["content"]
        response["entities"] = str(chat_response.get("metadata", {}).get("entities", ""))
        response["intents"] = str(chat_response.get("metadata", {}).get("intents", ""))
        response["knowledge"] = str(chat_response.get("metadata", {}).get("knowledge", ""))

        username = user["username"]
        sid = session_id or db_instance.create_session(username, "病例OCR识别")
        if sid:
            db_instance.save_message(sid, username, "user", f"[上传病例] {file.filename}")
            db_instance.save_message(
                sid, username, "assistant",
                chat_response["content"],
                str(chat_response.get("metadata", {}).get("entities", "")),
                str(chat_response.get("metadata", {}).get("intents", "")),
                str(chat_response.get("metadata", {}).get("knowledge", ""))
            )
            response["session_id"] = sid

    # 保存OCR结果到数据库
    db_instance.save_patient_report(
        username=user["username"],
        file_name=file.filename or "unknown",
        file_type=file.content_type or "image",
        raw_ocr_text=ocr_result.get("text", ""),
        structured_json=json.dumps(ocr_result.get("structured", {}), ensure_ascii=False),
        ocr_score=ocr_result.get("avg_score", 0.0)
    )

    return response   # 这一行是补充的，原第二段代码漏掉了

@router.post("/speech/stt")
async def speech_to_text(file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    """语音识别并生成回答"""
    content = await file.read()
    recognized_text = await speech_service.transcribe(content)
    
    if not recognized_text.startswith("语音识别失败") and recognized_text.strip():
        chat_response = await orchestrator.process(recognized_text, user["username"])
        return {
            "success": True,
            "text": recognized_text,
            "answer": chat_response["content"],
            "entities": str(chat_response.get("metadata", {}).get("entities", "")),
            "intents": str(chat_response.get("metadata", {}).get("intents", "")),
            "knowledge": str(chat_response.get("metadata", {}).get("knowledge", ""))
        }
    else:
        return {"success": True, "text": recognized_text}

@router.post("/speech/tts")
async def text_to_speech(request: TTSRequest, user: Dict = Depends(get_current_user)):
    """语音合成 — 返回 MP3 音频流"""
    result = await speech_service.synthesize(request.text, request.voice)
    if result:
        return Response(content=result, media_type="audio/mpeg")
    return {"success": False, "message": "TTS合成失败或服务不可用"}