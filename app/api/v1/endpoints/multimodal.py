from fastapi import APIRouter, Depends, UploadFile, File, Form
from app.core.security import get_current_user
from app.services.speech_service import speech_service
from app.services.image_service import image_service
from app.services.llm_service import llm_service
from app.services.ner_service import ner_service
from app.services.intent_service import intent_service
from app.services.kg_service import kg_service
from app.db.session import db_instance
from typing import Dict
import re
import json

router = APIRouter()

async def _get_chat_response(query: str, model_choice: str = None) -> dict:
    entities = ner_service.recognize(query)
    intent_res = await intent_service.recognize(query, model_choice)
    prompt, yitu, entities, _ = kg_service.generate_enhanced_prompt(intent_res, query, entities)

    full_response = ""
    async for chunk in llm_service.chat(prompt, model_choice, stream=True):
        full_response += chunk

    knowledge = "\n".join([
        f"提示{i+1}: {k}"
        for i, k in enumerate(re.findall(r'<提示>(.*?)</提示>', prompt))
        if len(k) >= 3
    ])

    return {
        "content": full_response,
        "entities": str(entities),
        "intents": yitu,
        "knowledge": knowledge,
        "prompt": prompt
    }

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
            "2. 判断是否存在术后风险点\n"
            "3. 给出通俗易懂的康复建议\n"
            "4. 如有异常，提示尽快联系医生\n\n"
            f"OCR文本如下：\n{ocr_result['text']}"
        )

        chat_response = await _get_chat_response(prompt_text)

        response["answer"] = chat_response["content"]
        response["entities"] = chat_response["entities"]
        response["intents"] = chat_response["intents"]
        response["knowledge"] = chat_response["knowledge"]

        # 可选：保存到聊天记录
        username = user["username"]
        sid = session_id or db_instance.create_session(username, "病例OCR识别")
        if sid:
            db_instance.save_message(sid, username, "user", f"[上传病例] {file.filename}")
            db_instance.save_message(
                sid,
                username,
                "assistant",
                chat_response["content"],
                chat_response["entities"],
                chat_response["intents"],
                chat_response["knowledge"]
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
    
    # 如果识别成功，自动生成回答
    if not recognized_text.startswith("语音识别失败") and recognized_text.strip():
        chat_response = await _get_chat_response(recognized_text)
        return {
            "success": True,
            "text": recognized_text,
            "answer": chat_response["content"],
            "entities": chat_response["entities"],
            "intents": chat_response["intents"],
            "knowledge": chat_response["knowledge"]
        }
    else:
        return {"success": True, "text": recognized_text}

@router.post("/speech/tts")
async def text_to_speech(text: str, user: Dict = Depends(get_current_user)):
    """语音合成"""
    result = await speech_service.synthesize(text)
    return {"success": True, "audio": result}